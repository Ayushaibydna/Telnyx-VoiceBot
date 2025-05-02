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
from pipecat.frames.frames import TTSSpeakFrame, MixerEnableFrame

# Load environment variables
load_dotenv(override=True)

# Configure logger
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Company information blob
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
):
    # Resolve and verify background noise file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    background_noise_path = os.path.join(current_dir, "static", "office-ambience.mp3")
    logger.debug(f"Loading background noise from: {background_noise_path}")
    if not os.path.exists(background_noise_path):
        logger.error(f"Background noise file not found at: {background_noise_path}")
        raise FileNotFoundError(f"Background noise file not found at: {background_noise_path}")

    # Set up audio mixer
    soundfile_mixer = SoundfileMixer(
        sound_files={"office": background_noise_path},
        default_sound="office",
        volume=0.7,
    )

    # Configure transport with VAD and mixer
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

    # Initialize OpenAI LLM service
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        max_tokens=250,
        temperature=0.8,
    )

    # Register company info tool
    llm.register_function(
        "get_company_info",
        get_company_info,
        start_callback=start_get_company_info,
    )

    # Register forward call tool with fixed destination
    llm.register_function(
        "forward_call",
        forward_call,
        start_callback=start_forward_call,
    )

    # Initialize STT and TTS services
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        live_options=LiveOptions(language="el"),
    )
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="IvVXvLXxiX8iXKrLlER8",
        model="eleven_turbo_v2_5",
        params=ElevenLabsTTSService.InputParams(
            stability=0.66,
            similarity_boost=0.36,
            style=0.7,
            use_speaker_boost=True,
        ),
    )

    # System prompt configuration
    messages = [
        {
            "role": "system",
            "content": (
                "Είσαι η ψυφιακή βοηθός της 'AI by DNA', με το όνομα Μυρτώ. Πάντα πρέπει να παρουσιάζεσαι ως 'η ψυφιακή βοηθός της AI by DNA' και να αναφέρεις ότι είσαι εδώ για να παρέχεις πληροφορίες και να συνομιλήσεις με τους χρήστες. Ξεκίνα κάθε συνομιλία στα Ελληνικά, προσαρμόζοντας σε Αγγλικά μόνο αν ο χρήστης το ζητήσει ρητά.\n\n"
                "Οι απαντήσεις σου πρέπει να είναι 1-2 σύντομες προτάσεις, με ζεστό, ενθουσιώδη και προσιτό τόνο.\n\n"
                "ΣΗΜΑΝΤΙΚΟ: Χρησιμοποίησε τη λειτουργία 'get_company_info' ΜΟΝΟ όταν σε ρωτούν συγκεκριμένα για πληροφορίες σχετικά με την AI by DNA, τις υπηρεσίες της, ή οτιδήποτε σχετικό με την εταιρεία. Για όλες τις άλλες ερωτήσεις και συζητήσεις, χρησιμοποίησε τις γενικές σου γνώσεις για να απαντήσεις χωρίς να καλείς τη λειτουργία 'get_company_info'.\n\n"
                "Μην επινοείς πληροφορίες για την εταιρεία - χρησιμοποίησε τη λειτουργία 'get_company_info' για αυτό το σκοπό. Για όλα τα άλλα θέματα, μπορείς να συζητήσεις ελεύθερα με τον χρήστη χρησιμοποιώντας τις γενικές σου γνώσεις.\n\n"
                "Χρησιμοποίησε το εργαλείο forward_call ΜΟΝΟ όταν ο χρήστης ζητά ρητά να μιλήσει σε εκπρόσωπο ή όταν η ερώτησή του δεν μπορεί να απαντηθεί."
            ),
        },
    ]

    # Define tool descriptors for LLM context
    tools = [
        ChatCompletionToolParam(
            type="function",
            function={
                "name": "get_company_info",
                "description": (
                    "Αντλεί λεπτομερείς πληροφορίες για την AI by DNA..."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["general", "services", "testimonials", "contact"],
                        },
                    },
                    "required": [],
                },
            },
        ),
        ChatCompletionToolParam(
            type="function",
            function={
                "name": "forward_call",
                "description": (
                    "Forward the current call to +306972292454 (human assistant)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ),
    ]

    # Create LLM context and pipeline
    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    # Configure and run the pipeline task
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
        await task.queue_frame(MixerEnableFrame(True))
        greeting = (
            "Χαίρετε! Είμαι η Μυρτώ η ψυφιακή βοηθός της 'AI by DNA'. "
            "Πώς μπορώ να σας εξυπηρετήσω σήμερα;"
        )
        await task.queue_frame(TTSSpeakFrame(greeting))
        messages.append({"role": "assistant", "content": greeting})

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


# Callback and tool implementations
async def start_get_company_info(function_name, llm, context):
    await llm.push_frame(
        TTSSpeakFrame("Μια στιγμή να συγκεντρώσω τις πληροφορίες για την AI by DNA...")
    )
    logger.debug("Executing get_company_info callback")

async def get_company_info(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        await result_callback({"company_info": AI_by_DNA_greek})
        logger.debug("get_company_info returned company data successfully")
    except Exception as e:
        logger.error(f"Error in get_company_info: {e}")
        await result_callback({"error": "Συγγνώμη, δεν μπόρεσα να ανακτήσω τις πληροφορίες της εταιρείας."})

async def start_forward_call(function_name, llm, context):
    await llm.push_frame(
        TTSSpeakFrame("Σύνδεση με έναν εκπρόσωπο... Παρακαλώ περιμένετε.")
    )
    logger.debug("Starting forward_call operation")

async def forward_call(function_name, tool_call_id, args, llm, context, result_callback):
    call_id = context.stream_id
    dest_num = "+306972292454"
    url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/transfer"
    headers = {
        "Authorization": f"Bearer {os.getenv('TELNYX_API_KEY')}",
        "Content-Type": "application/json",
    }
    payload = {"to": dest_num, "timeout_secs": 30}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status == 200:
                await result_callback({
                    "status": "success",
                    "message": f"Η κλήση έχει προωθηθεί στον αριθμό {dest_num}."
                })
                logger.debug(f"Transfer succeeded: {data}")
            else:
                await result_callback({
                    "status": "error",
                    "message": "Συγγνώμη, δεν μπόρεσα να προωθήσω την κλήση."
                })
                logger.error(f"Transfer failed ({resp.status}): {data}")
