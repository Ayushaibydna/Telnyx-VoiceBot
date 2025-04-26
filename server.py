#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import json
import os
import telnyx
import uvicorn
from bot import run_bot
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
import requests
import sys
from loguru import logger


app = FastAPI()

# Set Telnyx API Key
telnyx.api_key = os.getenv("TELNYX_API_KEY")

# Mount the static directory for audio files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable CORS to avoid restrictions while using the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: Configure logger if not already done
logger.remove()
logger.add(sys.stderr, level="DEBUG")


@app.post("/")
async def start_call(request: Request):
    """
    Handles incoming calls from real phones.
    """
    try:
        body = await request.json()
        logger.debug(f"Telnyx Inbound Call Webhook Payload: {json.dumps(body, indent=2)}")

        # ✅ Extract Call ID
        call_id = body.get("data", {}).get("payload", {}).get("call_control_id")
        if call_id:
            logger.info(f"Received call.initiated event for call_control_id: {call_id}")
        else:
            logger.error("Could not extract call_control_id from incoming webhook.")
            return JSONResponse(content={"error": "Invalid request"}, status_code=400)

        logger.info(f"Answering Call: {call_id} with streaming to wss://davilas-test-production.up.railway.app/ws")

        # ✅ Answer the call and enable streaming in one request
        api_url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer"
        #stream_url = "wss://davilas-test-production.up.railway.app/ws"  # Ensure this WebSocket is live!
        stream_url = "ws://telnyx-voicebot-production.up.railway.app/ws"

        headers = {
            "Authorization": f"Bearer {telnyx.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "stream_url": stream_url,
            "stream_track": "both_tracks",  # ✅ Streaming both inbound & outbound audio
            "stream_bidirectional_mode": "rtp",  # ✅ Change to mp3 if needed
            "stream_bidirectional_codec": "PCMU",  # ✅ Codec choice (PCMU, PCMA, G722, etc.)
            "send_silence_when_idle": True,  # ✅ Keeps stream open even if no one is speaking
        }

        response = requests.post(api_url, headers=headers, json=payload)

        if response.status_code == 200:
            logger.info(f"✅ Call {call_id} answered successfully via API.")
            return JSONResponse(content={"message": "Call answered, streaming started"}, status_code=200)
        else:
            logger.error(f"❌ Error answering call {call_id} via API: {response.status_code} - {response.text}")
            return JSONResponse(content={"error": response.json()}, status_code=response.status_code)

    except telnyx.error.APIError as api_err:
        logger.error(f"Telnyx API Error in start_call: {str(api_err)}")
        return JSONResponse(content={"error": str(api_err)}, status_code=500)

    except Exception as e:
        logger.error(f"Unexpected Error in start_call: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    call_control_id = None # Initialize
    stream_id = None
    try:
        logger.info("WebSocket connection accepted. Waiting for Telnyx 'start' event...")
        # Telnyx sends a 'start' event as the first message
        start_event_raw = await websocket.receive_text()
        start_event = json.loads(start_event_raw)

        # Log the received start event for debugging path to call_control_id
        logger.debug(f"Received WebSocket Start Event: {json.dumps(start_event, indent=2)}")

        if start_event.get("event") == "start":
            stream_id = start_event.get("stream_id")
            # --- VERIFY THIS PATH ---
            # Check the logged start_event to confirm the exact location of call_control_id
            # Common location: start_event["start"]["call_control_id"]
            call_control_id = start_event.get("start", {}).get("call_control_id")
            # --- END VERIFICATION ---

            outbound_encoding = start_event.get("start", {}).get("media_format", {}).get("encoding")

            if not stream_id or not call_control_id or not outbound_encoding:
                logger.error(f"Missing critical info in WebSocket start event: stream_id={stream_id}, call_control_id={call_control_id}, encoding={outbound_encoding}")
                # Close with an appropriate code and reason
                await websocket.close(code=1008, reason="Missing critical info in start event")
                return # Stop further processing

            logger.info(f"WebSocket stream started: stream_id={stream_id}, call_control_id={call_control_id}, outbound_encoding={outbound_encoding}")

            # === Pass call_control_id to the bot logic ===
            await run_bot(
                websocket,
                stream_id,
                outbound_encoding, # Encoding Telnyx expects us to send
                "PCMU",            # Encoding we told Telnyx to send us (inbound)
                call_control_id    # <-- Pass the extracted ID here
            )
            # === End of run_bot call ===

        else:
            logger.warning(f"Received unexpected first message on WebSocket (expected 'start' event): {start_event.get('event')}")
            await websocket.close(code=1002, reason="Protocol error: Expected start event")

    except WebSocketDisconnect:
        # This is expected when the call ends or is transferred
        logger.info(f"WebSocket disconnected for stream {stream_id or 'unknown'}. Code: {websocket.client_state}")
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from WebSocket.")
        # Avoid immediate close if possible, maybe log and continue if state allows
    except Exception as e:
        logger.exception(f"Error in WebSocket handler for stream {stream_id or 'unknown'}: {e}")
        # Try to close gracefully on unexpected errors
        if websocket.client_state != websocket.client_state.DISCONNECTED:
            await websocket.close(code=1011, reason=f"Internal server error")
    finally:
        logger.info(f"WebSocket connection processing finished for stream {stream_id or 'unknown'}.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    uvicorn.run(app, host="0.0.0.0", port=port)
