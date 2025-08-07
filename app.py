import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
import os
import subprocess
import time
import pygame
import tempfile

# ================================
# 🔧 Start Ollama Server (if not running)
# ================================
def start_ollama():
    if not st.session_state.get("ollama_started"):
        with st.spinner("🔁 Starting Ollama server... This may take a moment."):
            try:
                st.session_state.ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                time.sleep(8)
                st.session_state.ollama_started = True
                st.success("✅ Ollama is ready! Ava is warming up...")
            except Exception as e:
                st.error(f"❌ Failed to start Ollama: {e}")
                st.info("Make sure Ollama is installed: [ollama.com](https://ollama.com)")

start_ollama()

# ================================
# 🌸 Title & Welcome Message
# ================================
st.title("🌸 Ava - Your Compassionate Companion")

st.markdown("""
Hi there, I'm Ava 💖  
I'm here to listen — without judgment, without rush.  
Whatever you're feeling, it's okay. You're safe here.
""")

# ================================
# 🧠 Initialize Session State
# ================================
if "chat" not in st.session_state:
    st.session_state.chat = []
if "mood_logs" not in st.session_state:
    st.session_state.mood_logs = []
if "mood_history" not in st.session_state:
    st.session_state.mood_history = []



# ================================
# 🔍 Mood Detection Function
# ================================
def detect_mood(text):
    text_lower = text.lower()
    mood_scores = {
        "happy": ["joy", "great", "amazing", "love", "good", "excited", "glad", "grateful", "peaceful"],
        "sad": ["sad", "down", "tears", "cry", "grief", "empty", "hopeless", "grieving", "lonely", "alone"],
        "anxious": ["anxious", "nervous", "worry", "panic", "overwhelm", "scared", "afraid", "stressed", "racing", "edgy"],
        "angry": ["angry", "mad", "frustrated", "hate", "irritated", "furious", "resent", "rage"],
        "tired": ["tired", "exhausted", "drained", "burnt out", "sleepy", "weary"]
    }
    detected = "neutral"
    max_score = 0
    for mood, keywords in mood_scores.items():
        score = sum(1 for word in keywords if word in text_lower)
        if score > max_score:
            max_score = score
            detected = mood
    return detected

# ================================
# 📁 Load Mood Logs from File (Persistence)
# ================================
LOG_FILE = "data/mood_logs.json"
if os.path.exists(LOG_FILE):
    try:
        with open(LOG_FILE, "r") as f:
            saved_logs = json.load(f)
            st.session_state.mood_logs = saved_logs
            for log in saved_logs:
                st.session_state.mood_history.append({
                    "timestamp": log["timestamp"],
                    "mood": log["mood"].split(" ")[1] if log["mood"] else "neutral"
                })
    except:
        st.session_state.mood_logs = []
        st.session_state.mood_history = []

# ================================
# 🌿 Sidebar: Mood Tracker
# ================================
st.sidebar.header("🌿 How are you today?")
st.sidebar.markdown("Pick a mood — no feeling is too small.")
mood_options = ["😊 Happy", "😢 Sad", "😟 Anxious", "😠 Angry", "😐 Neutral", "😴 Tired", "🧘‍♀️ Calm"]
selected_mood = st.sidebar.selectbox("", mood_options, label_visibility="collapsed")

if st.sidebar.button("Log Mood"):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mood": selected_mood
    }
    st.session_state.mood_logs.append(entry)
    st.session_state.mood_history.append({
        "timestamp": entry["timestamp"],
        "mood": selected_mood.split(" ")[1]
    })
    os.makedirs("data", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(st.session_state.mood_logs, f, indent=2)
    st.sidebar.success(f"Mood logged: {selected_mood}")

# Show mood history
if st.session_state.mood_logs:
    st.sidebar.subheader("Your Mood Journal")
    df = pd.DataFrame(st.session_state.mood_logs)
    st.sidebar.dataframe(df.tail(7), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("💬 You're not alone.")
st.sidebar.markdown("🌼 Breathe. Share. Be held.")

# ================================
# 🔊 ElevenLabs Text-to-Speech
# ================================
def speak_with_elevenlabs(text, api_key):
    try:
        VOICE_ID = "Fd20ovrtdRUSfknSexl2"  # Your voice ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": api_key}
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.2,
                "use_speaker_boost": True
            }
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            st.error(f"❌ ElevenLabs error: {response.status_code} - {response.text}")
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            temp_path = f.name
        with open(temp_path, 'wb') as f:
            f.write(response.content)

        pygame.mixer.init()
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.quit()
        os.unlink(temp_path)

    except Exception as e:
        st.error(f"🔊 Audio error: {str(e)}")

# ================================
# 🔐 Load ElevenLabs API Key
# ================================
try:
    ELEVENLABS_API_KEY = st.secrets["elevenlabs_api_key"]
except:
    st.warning("🔊 Voice disabled: Add your ElevenLabs API key to `.streamlit/secrets.toml`")
    ELEVENLABS_API_KEY = None

# Voice toggle
enable_voice = st.sidebar.checkbox("🔊 Ava speaks back", value=True, key="enable_voice")

# ================================
# 💬 Chat History
# ================================
for message in st.session_state.chat:
    if message["role"] in ["user", "assistant"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# ================================
# 🖊️ User Input & AI Response
# ================================
user_input = st.chat_input("Share what's on your mind...")

if user_input:
    # Add user message
    st.session_state.chat.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Detect mood
    current_mood = detect_mood(user_input)
    st.session_state.mood_history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mood": current_mood
    })

    # Build emotional context
    recent_moods = [m["mood"] for m in st.session_state.mood_history[-5:]]
    mood_context = ""
    if recent_moods.count("sad") >= 2:
        mood_context = "I've noticed sadness has been with you lately. It means a lot that you keep sharing your heart."
    elif recent_moods.count("anxious") >= 2:
        mood_context = "Anxiety has come up again. I'm here with you in this wave — you don’t have to calm it right now."
    elif recent_moods.count("tired") >= 2:
        mood_context = "You've mentioned feeling drained a few times. That kind of exhaustion takes real courage to carry."
    elif current_mood == "happy":
        mood_context = "I can feel a lightness in your words. I'm glad you're having a gentle moment."
    elif current_mood == "neutral":
        mood_context = "You're holding space for something — I'm here, quietly with you."

    # Generate response
    try:
        full_prompt = f"[INST] {mood_context}\nUser: {user_input} [/INST]"
        with st.spinner("💭 Ava is listening..."):
            time.sleep(0.5)

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "ava",
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.75, "top_p": 0.9, "num_ctx": 8192}
            },
            timeout=60
        )

        if response.status_code == 200:
            bot_msg = response.json()["response"].strip()
            bot_msg = bot_msg.replace("[/INST]", "").replace("Ava:", "").strip()
        else:
            bot_msg = f"❌ Ollama error {response.status_code}: {response.text}"

    except requests.exceptions.ConnectionError:
        bot_msg = "❌ Cannot connect to Ollama. Is it running?"
    except requests.exceptions.Timeout:
        bot_msg = "⏳ Took too long to respond. Try again?"
    except Exception as e:
        bot_msg = f"⚠️ Sorry, I couldn't respond: {str(e)}"

    # Add bot response
    st.session_state.chat.append({"role": "assistant", "content": bot_msg})
    with st.chat_message("assistant"):
        st.write(bot_msg)

        # Speak if enabled
        if enable_voice and ELEVENLABS_API_KEY:
            with st.spinner("🔊 Ava is speaking..."):
                speak_with_elevenlabs(bot_msg, ELEVENLABS_API_KEY)

# ================================
# 🌼 Footer
# ================================
st.markdown("""
---
MindBloom 🌸 A safe space to feel.  
Not a replacement for therapy — just a kind companion.
""")