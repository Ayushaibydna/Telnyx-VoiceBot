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
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
import requests


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


@app.post("/")
async def start_call(request: Request):
    """
    Handles incoming calls from real phones.
    """
    try:
        body = await request.json()
        print("Inbound Call:", json.dumps(body, indent=2))

        # ✅ Extract Call ID
        call_id = body.get("data", {}).get("payload", {}).get("call_control_id")
        if not call_id:
            return JSONResponse(content={"error": "Invalid request"}, status_code=400)

        print(f"Answering Call: {call_id} with streaming enabled")

        # ✅ Answer the call and enable streaming in one request
        api_url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer"
        stream_url = "wss://telnyx-voicebot-production.up.railway.app/ws"  # Ensure this WebSocket is live!
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

        if response.status_code != 200:
            print(f"❌ Error answering call with streaming: {response.text}")
            return JSONResponse(content={"error": response.json()}, status_code=response.status_code)

        print(f"✅ Call {call_id} answered and streaming requested.")
        return JSONResponse(content={"message": "Call answered, streaming started"}, status_code=200)

    except telnyx.error.APIError as api_err:
        print(f"Telnyx API Error in start_call: {str(api_err)}")
        return JSONResponse(content={"error": str(api_err)}, status_code=500)

    except Exception as e:
        print(f"Unexpected Error in start_call: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    start_data = websocket.iter_text()
    await start_data.__anext__()
    call_data = json.loads(await start_data.__anext__())
    print(call_data, flush=True)
    stream_id = call_data["stream_id"]
    outbound_encoding = call_data["start"]["media_format"]["encoding"]
    print("WebSocket connection accepted")
    await run_bot(websocket, stream_id, outbound_encoding, "PCMU")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    uvicorn.run(app, host="0.0.0.0", port=port)
