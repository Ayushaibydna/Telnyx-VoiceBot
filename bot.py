#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import sys
import aiohttp

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.mixers.soundfile_mixer import SoundfileMixer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.serializers.telnyx import TelnyxFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from deepgram import LiveOptions
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from openai.types.chat import ChatCompletionToolParam
from pipecat.frames.frames import Frame, TTSSpeakFrame, MixerEnableFrame, UserStoppedSpeakingFrame


load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


AI_by_DNA_greek = f"""
Ενδυναμώνουμε οργανισμούς με Agentic AI
AI by DNA – Ένας οργανισμός μετασχηματισμού μέσω Τεχνητής Νοημοσύνης που υποστηρίζει τις σύγχρονες επιχειρήσεις στην κλιμάκωση των δυνατοτήτων τους σε AI και Data, ενισχύοντας την αποδοτικότητα, την απόδοση και την ανάπτυξη.
Είμαστε ο αξιόπιστος συνεργάτης σας για να καθοδηγήσουμε τον AI μετασχηματισμό σας. Η ομάδα μας αποτελείται από data scientists, AI engineers, software developers, digital innovation και cross-market experts. Διαθέτουμε το δικό μας AI Factory, όπου πειραματιζόμαστε, αναπτύσσουμε και υλοποιούμε agentic λύσεις για εσάς.
Γνωσιακοί Βοηθοί - Knowledge Assistants
Στο σύγχρονο περιβάλλον, η γρήγορη πρόσβαση σε ακριβείς πληροφορίες και η δυνατότητα αξιόπιστης δράσης είναι καθοριστικοί παράγοντες για τη βελτίωση της αποδοτικότητας.
Μοναδική Εστίαση στην Εσωτερική Ανάκτηση Δεδομένων
Οι βοηθοί της AI by DNA εξειδικεύονται στην ανάκτηση εσωτερικών πληροφοριών, αντλώντας δεδομένα από πολλαπλές πηγές. Αυτό σημαίνει βελτιστοποιημένες ροές πληροφοριών, εξασφαλίζοντας ακρίβεια, αποδοτικότητα και ασφάλεια στη διαδικασία 
αναζήτησης, αναθεώρησης και περίληψης πληροφοριών.
Αυξήστε την αποδοτικότητα της επιχείρησής σας
Μειώστε τη χειρωνακτική εργασία
Βελτιώστε τις ροές εργασιών μέσω AI για αξιολόγηση, αναφορές & συμμόρφωση με κανονισμούς και πρότυπα
Συνομιλιακοί Πράκτορες (Conversational Agents)
Μετατρέπουμε τη φυσική γλώσσα στο νέο περιβάλλον διεπαφής με τα δεδομένα και το επιχειρηματικό σας περιεχόμενο. Οι AI-driven Συνομιλιακοί Πράκτορες προσφέρουν προσωποποιημένη, σε πραγματικό χρόνο και εις βάθος αλληλεπίδραση.
Ανακαλύψτε νέες δυνατότητες με το AI by Chat
Προσωποποιήστε, ενημερώστε, προτείνετε, προωθήστε και υποστηρίξτε
Αποκτήστε και διατηρήστε πελάτες
Απελευθερώστε τη δύναμη του AI by Phone
Οι ανθρωποκεντρικοί AI Voice Assistants μεταμορφώνουν τον τρόπο χρήσης των τηλεφωνικών γραμμών
Βελτιώστε τη διαθεσιμότητα επικοινωνίας, την πολυγλωσσική κάλυψη και την ικανοποίηση των πελατών
Επεκτείνετε τις δυνατότητες σας με το AI by Clone
Video-based agents που χρησιμοποιούν ανθρώπινα avatars
Αλληλεπιδρούν και συνομιλούν με τους πελάτες στο δικό σας γνωσιακό πλαίσιοΜεταμορφώστε την εμπειρία των phygital πελατών σας
Μηχανές Υποστήριξης Αποφάσεων - Decision Support Engines
Data Pipeline & Predictive Analytics για Στρατηγικές Επιλογές
Σε έναν κόσμο όπου τα δεδομένα οδηγούν την καινοτομία, οι δυνατότητες επεξεργασίας και ανάλυσης δεδομένων της AI by DNA σας βοηθούν να αποκτήσετε χρήσιμες, δράσιμες πληροφορίες από σύνθετα σύνολα δεδομένων.
Λήψη αποφάσεων βάσει δεδομένων σε πραγματικό χρόνο
Βελτιστοποίηση διαχείρισης πόρων
Συνολική διαχείριση αποθεμάτων
Δυναμική τιμολόγηση σε πραγματικό χρόνο
Ψάχνετε να αξιοποιήσετε προηγμένα γλωσσικά μοντέλα με βάση τα δεδομένα;
Χρειάζεστε προσαρμοσμένους AI πράκτορες με δυνατότητες ανάκτησης, ανάληψης δράσης ή πρόβλεψης, και άψογη ενσωμάτωση σε vector stores και άλλα εργαλεία;
Σχεδιάζουμε, αναπτύσσουμε και υλοποιούμε εξατομικευμένες λύσεις AI που εξυπηρετούν τους συγκεκριμένους επιχειρηματικούς σας στόχους.
Μετατρέψτε τα δεδομένα σας σε Δράσιμη Νοημοσύνη!
Testimonial
Γιώργος Κοτζαμάνης, Συνιδρυτής | Head of AI Factory
Προσθέστε το AI στο DNA της επιχείρησής σας
"Ζούμε σε μια εποχή μαζικής τεχνολογικής ανατροπής σε όλους τους τομείς εργασίας και ζωής. Ήμασταν προετοιμασμένοι γι' αυτό, εργαζόμαστε πάνω του, και τώρα είναι η στιγμή να επικεντρωθούμε σε αυτά που μπορούμε να επιτύχουμε για εσάς."
Κώστας Βαρσάμος, Συνιδρυτής | Managing Partner
AI για Προσωποποιημένη Εμπειρία Καταναλωτή
Βοηθός Αυτοεξυπηρέτησης
"Η AI by DNA φέρνει επανάσταση στον τρόπο επικοινωνίας των πληροφοριών προϊόντων στους πελάτες μας, μετατρέποντάς τις σε μια εμπειρία φυσικής συνομιλίας!"
Σπύρος Μπόκιας
Συνιδρυτής & CEO στην iPHARMA S.A.
Γραφεία: Ελλάδα (Αθήνα) | Γερμανία (Φρανκφούρτη)
Email: contact@aibydna.com
Copyright © 2024-2025 AIbyDNA.com – Όλα τα δικαιώματα διατηρούνται.
"""


async def run_bot(
    websocket_client,
    stream_id: str,
    outbound_encoding: str,
    inbound_encoding: str,
    call_control_id: str = None,  # Add call_control_id parameter (default None for backward compatibility)
):
    
    # More robust path resolution for the audio file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    background_noise_path = os.path.join(current_dir, "static", "office-ambience.mp3")
    
    # Add debug logging
    logger.debug(f"Loading background noise from: {background_noise_path}")
    if not os.path.exists(background_noise_path):
        logger.error(f"Background noise file not found at: {background_noise_path}")
        raise FileNotFoundError(f"Background noise file not found at: {background_noise_path}")
    
    soundfile_mixer = SoundfileMixer(
        sound_files={"office": background_noise_path},
        default_sound="office",
        volume=0.7,
    )
    
    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_out_enabled=True,
            audio_out_mixer=soundfile_mixer,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=TelnyxFrameSerializer(stream_id, outbound_encoding, inbound_encoding),
        ),
    )

    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o", max_tokens=250, temperature=0.8)

    # --- Forward Call Tool Handler ---
    target_number = os.getenv("FORWARD_NUMBER")
    async def handle_forward_call_tool(function_name, tool_call_id, args, llm_service, context, result_callback):
        logger.info(f"Tool call received: {function_name}")
        if not call_control_id:
            logger.error("Cannot forward call: call_control_id is missing.")
            await result_callback({"error": "Internal error: Call identifier missing."})
            return
        if not target_number:
            logger.error("Cannot forward call: FORWARD_NUMBER is not set.")
            await result_callback({"error": "Internal error: Forwarding number not configured."})
            return
        await execute_forward_call_action(call_control_id, target_number, llm_service, result_callback)

    # --- System Prompt Update ---
    messages = [
        {
            "role": "system",
            "content": (
                "Είσαι η ψυφιακή βοηθός της 'AI by DNA', με το όνομα Μυρτώ. Πάντα πρέπει να παρουσιάζεσαι ως 'η ψυφιακή βοηθός της AI by DNA' και να αναφέρεις ότι είσαι εδώ για να παρέχεις πληροφορίες και να συνομιλήσεις με τους χρήστες. Ξεκίνα κάθε συνομιλία στα Ελληνικά, προσαρμόζοντας σε Αγγλικά μόνο αν ο χρήστης το ζητήσει ρητά.\n\n"
                "Οι απαντήσεις σου πρέπει να είναι 1-2 σύντομες προτάσεις, με ζεστό, ενθουσιώδη και προσιτό τόνο.\n\n"
                "ΔΙΑΘΕΣΙΜΑ ΕΡΓΑΛΕΙΑ:\n"
                "1.  `get_company_info`: Χρησιμοποίησε αυτό ΜΟΝΟ όταν σε ρωτούν συγκεκριμένα για πληροφορίες σχετικά με την AI by DNA (π.χ. υπηρεσίες, ομάδα, προϊόντα, εταιρικές πληροφορίες). Μην επινοείς πληροφορίες για την εταιρεία.\n"
                "2.  `forward_call`: Χρησιμοποίησε αυτό ΜΟΝΟ όταν ο χρήστης ζητήσει ρητά να μεταφερθεί η κλήση του ή λέει φράσεις όπως 'Μεταφέρετέ με', 'Θέλω να μιλήσω με κάποιον άνθρωπο', 'Σύνδεσέ με με έναν εκπρόσωπο', 'Transfer my call'. Μην προσφέρεσαι να μεταφέρεις την κλήση εκτός αν στο ζητήσουν ρητά.\n\n"
                "ΓΙΑ ΟΛΕΣ τις άλλες ερωτήσεις και συζητήσεις, χρησιμοποίησε τις γενικές σου γνώσεις για να απαντήσεις ΧΩΡΙΣ να καλείς καμία λειτουργία."
            ),
        },
    ]

    # --- Tools List Update ---
    tools = [
        ChatCompletionToolParam(
            type="function",
            function={
                "name": "get_company_info",
                "description": "Αντλεί λεπτομερείς πληροφορίες για την AI by DNA, τις υπηρεσίες και τις λύσεις της. Χρησιμοποίησε αυτή τη λειτουργία ΜΟΝΟ για ερωτήσεις σχετικά με την εταιρεία AI by DNA.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["general", "services", "testimonials", "contact"],
                            "description": "Το είδος των πληροφοριών που ζητάει ο χρήστης (προαιρετικό)"
                        }
                    },
                    "required": []
                },
            },
        ),
        ChatCompletionToolParam(
            type="function",
            function={
                "name": "forward_call",
                "description": "Μεταφέρει την τρέχουσα τηλεφωνική κλήση σε έναν προκαθορισμένο αριθμό. Χρησιμοποίησε αυτό ΜΟΝΟ όταν ο χρήστης ζητήσει ρητά να μεταφερθεί η κλήση (π.χ. 'Μεταφέρετέ με', 'Transfer my call', 'Θέλω να μιλήσω με άνθρωπο').",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        )
    ]
    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)

    # Register tools
    llm.register_function("get_company_info", get_company_info, start_callback=start_get_company_info)
    llm.register_function("forward_call", handle_forward_call_tool, start_callback=start_forward_call)

    stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            live_options=LiveOptions(
                language="el"
            )
        )
            
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="IvVXvLXxiX8iXKrLlER8",
        model="eleven_turbo_v2_5",
        params=ElevenLabsTTSService.InputParams(
            stability=0.66,
            similarity_boost=0.36,
            style=0.7,
            use_speaker_boost=True
        )
    )
    
    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            context_aggregator.user(),
            llm,  # LLM with tool support!
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            report_only_initial_ttfb=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Enable the background noise mixer
        await task.queue_frame(MixerEnableFrame(True))
        
        # Create a specific greeting message to be spoken immediately
        greeting_message = "Χαίρετε! Είμαι η Μυρτώ η ψυφιακή βοηθός της 'AI by DNA'. Πώς μπορώ να σας εξυπηρετήσω σήμερα;"
        
        # Queue a direct speech frame to be spoken immediately
        await task.queue_frame(TTSSpeakFrame(greeting_message))
        
        # Add the greeting as an assistant message in the conversation history
        messages.append({
            "role": "assistant",
            "content": greeting_message
        })

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)

# Update start_get_company_info to push UserStoppedSpeakingFrame
async def start_get_company_info(function_name, llm, context):
    await llm.push_frame(TTSSpeakFrame("Μια στιγμή να συγκεντρώσω τις πληροφορίες για την AI by DNA..."))
    await llm.push_frame(UserStoppedSpeakingFrame())
    logger.debug(f"Executing get_company_info for context enhancement")

# ENHANCED get_company_info function with error handling
async def get_company_info(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        # For now, return all company information
        await result_callback({"company_info": AI_by_DNA_greek})
        logger.debug(f"Successfully retrieved and returned company information")
    except Exception as e:
        logger.error(f"Error in get_company_info: {str(e)}")
        await result_callback({"error": "Συγγνώμη, δεν μπόρεσα να ανακτήσω τις πληροφορίες της εταιρείας."})

# --- Forward Call Tool Implementation ---
async def execute_forward_call_action(call_control_id: str, target_number: str, llm_service, result_callback):
    """Makes the Telnyx API call to transfer the call using aiohttp."""
    api_key = os.getenv("TELNYX_API_KEY")
    if not api_key:
        logger.error("TELNYX_API_KEY environment variable not set.")
        await result_callback({"error": "Δεν ήταν δυνατή η μεταφορά της κλήσης λόγω προβλήματος διαμόρφωσης."})
        return
    if not target_number:
        logger.error("FORWARD_NUMBER environment variable not set.")
        await result_callback({"error": "Δεν ήταν δυνατή η μεταφορά της κλήσης. Ο αριθμός προορισμού λείπει."})
        return

    transfer_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/transfer"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"to": target_number}

    logger.info(f"Attempting to transfer call {call_control_id} to {target_number}")
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post(transfer_url, json=payload) as response:
                response_text = await response.text()
                if response.status >= 200 and response.status < 300:
                    try:
                        response_data = await response.json(content_type=None)
                        logger.info(f"Successfully initiated call transfer for {call_control_id}. Status: {response.status}, Response: {response_data}")
                    except Exception:
                        logger.info(f"Successfully initiated call transfer for {call_control_id}. Status: {response.status}, Response: {response_text}")
                    await result_callback({"status": "Transfer initiated successfully."})
                else:
                    logger.error(f"Error transferring call {call_control_id}: {response.status} - {response_text}")
                    error_message = f"Συγγνώμη, παρουσιάστηκε ένα πρόβλημα ({response.status}) κατά τη μεταφορά της κλήσης."
                    await result_callback({"error": error_message})
        except aiohttp.ClientError as e:
            logger.error(f"AIOHTTP ClientError transferring call {call_control_id}: {e}")
            await result_callback({"error": "Παρουσιάστηκε σφάλμα δικτύου κατά τη μεταφορά."})
        except Exception as e:
            logger.exception(f"Unexpected error during call transfer for {call_control_id}: {e}")
            await result_callback({"error": "Παρουσιάστηκε ένα μη αναμενόμενο σφάλμα κατά τη μεταφορά."})

async def start_forward_call(function_name, llm, context):
    """Provides TTS feedback when forward_call is initiated."""
    logger.debug(f"LLM initiated function: {function_name}. Providing feedback.")
    await llm.push_frame(TTSSpeakFrame("Εντάξει, μεταφέρω την κλήση σας τώρα..."))
    await llm.push_frame(UserStoppedSpeakingFrame())