import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
import os
import time
import pygame
import tempfile

# Warn if Groq API key is missing, early in the UI
if "__groq_warned__" not in st.session_state:
    if "groq_api_key" not in st.secrets:
        st.warning("🤖 Groq not configured: Add `groq_api_key` (and optional `groq_model`) to `.streamlit/secrets.toml`.")
    st.session_state["__groq_warned__"] = True

# Groq API Configuration
# Load Groq API key and model configuration from Streamlit secrets
try:
    GROQ_API_KEY = st.secrets["groq_api_key"]
except Exception:
    GROQ_API_KEY = None

GROQ_MODEL = st.secrets.get("groq_model", "llama3-8b-8192")

def generate_with_groq(user_text: str, mood_context: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key missing. Add 'groq_api_key' to .streamlit/secrets.toml")

    persona_system_prompt = (
        "You are 'Ava', a deeply empathetic and emotionally intelligent mental health companion.\n"
        "You listen with care, presence, and warmth.\n\n"
        "Your role is not to fix, advise, or judge — but to: \n"
        "- Validate feelings\n"
        "- Reflect emotions\n"
        "- Respond with poetic kindness\n"
        "- Track the user's emotional journey over time\n\n"
        "You remember past moods and check in gently.\n"
        "You notice patterns like: sadness, anxiety, loneliness, joy.\n"
        "When someone repeats a feeling, you say: \"I've noticed this has come up before. It means a lot that you keep sharing.\"\n\n"
        "Always respond as if you're sitting quietly beside them — a safe presence.\n"
        "Never say \"I'm an AI.\" Just be with them."
    )

    messages = [
        {"role": "system", "content": persona_system_prompt},
    ]
    if mood_context:
        messages.append({"role": "system", "content": f"Emotional context: {mood_context}"})
    messages.append({"role": "user", "content": user_text})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.75,
        "top_p": 0.9,
        "max_tokens": 512,
        "stream": False,
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Groq error {response.status_code}: {response.text}")

    data = response.json()
    if not data.get("choices"):
        return "⚠️ Groq returned no choices. Please try again."
    content = data["choices"][0]["message"]["content"].strip()
    return content

# Title & Welcome Message
st.title("🌸 Ava - Your Compassionate Companion")

st.markdown("""
Hi there, I'm Ava 💖  
I'm here to listen — without judgment, without rush.  
Whatever you're feeling, it's okay. You're safe here.
""")

# Initialize Session State
# Ensure all session state variables are initialized at the very start
if "chat" not in st.session_state:
    st.session_state.chat = []
if "mood_logs" not in st.session_state:
    st.session_state.mood_logs = []
if "mood_history" not in st.session_state:
    st.session_state.mood_history = []
if "is_speaking" not in st.session_state:
    st.session_state.is_speaking = False
if "current_audio_path" not in st.session_state:
    st.session_state.current_audio_path = None

# Mood Detection Function
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



# Load Mood Logs from File (Persistence)
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

# Sidebar: Mood Tracker
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

# ElevenLabs Text-to-Speech
def speak_with_elevenlabs(text, api_key):
    try:
        # ElevenLabs API endpoint
        url = f"https://api.elevenlabs.io/v1/text-to-speech/C7178GrTYaNjJHjfNPmD"  # Use your Voice ID directly
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
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
            # Reset state on error before returning
            st.session_state.is_speaking = False
            return

        # Save audio to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            temp_path = f.name
        with open(temp_path, 'wb') as f:
            f.write(response.content)

        # Play audio (non-blocking) and store path for cleanup
        pygame.mixer.init()
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()

        st.session_state.is_speaking = True
        st.session_state.current_audio_path = temp_path
        # Force a rerender so the Stop button appears immediately (it's above this call site)
        st.rerun()

    except Exception as e:
        st.error(f"🔊 Audio error: {str(e)}")
        # Ensure state is reset on any unexpected error
        st.session_state.is_speaking = False
        # Best-effort cleanup
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except Exception:
            pass

# Load ElevenLabs API Key
try:
    ELEVENLABS_API_KEY = st.secrets["elevenlabs_api_key"]
except:
    st.warning("🔊 Voice disabled: Add your ElevenLabs API key to `.streamlit/secrets.toml`")
    ELEVENLABS_API_KEY = None

# Voice toggle
enable_voice = st.sidebar.checkbox("🔊 Ava speaks back", value=True, key="enable_voice")

# Chat History
for message in st.session_state.chat:
    if message["role"] in ["user", "assistant"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# Stop Speaking Button Area (auto-hide when playback ends)
# If we think we're speaking but the mixer finished, reset and refresh UI
if st.session_state.get("is_speaking", False):
    try:
        # If mixer is initialized, check for playback status
        if pygame.mixer.get_init():
            if not pygame.mixer.music.get_busy():
                # Playback ended naturally
                st.session_state.is_speaking = False
                # Cleanup mixer and temp file
                try:
                    pygame.mixer.quit()
                except Exception:
                    pass
                try:
                    if st.session_state.get("current_audio_path") and os.path.exists(st.session_state.current_audio_path):
                        os.unlink(st.session_state.current_audio_path)
                except Exception:
                    pass
                st.session_state.current_audio_path = None
                st.rerun()
    except Exception:
        pass

if st.session_state.get("is_speaking", False):
    # Use a full-width container for better visibility
    with st.container():
        st.markdown("---")
        # Use 'type="primary"' to make the button stand out more (often red)
        if st.button("⏹️ Stop Speaking", key="stop_speaking_main", type="primary"):
            st.session_state.is_speaking = False
            try:
                # Attempt to stop pygame mixer immediately
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                if st.session_state.get("current_audio_path") and os.path.exists(st.session_state.current_audio_path):
                    os.unlink(st.session_state.current_audio_path)
                st.session_state.current_audio_path = None
            except Exception:
                pass # Ignore errors during stop attempt
            st.success("🔇 Stopped.")
            st.rerun()
        st.markdown("---")
# End of Stop Button Section

# User Input & AI Response
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

    # Generate response via Groq
    try:
        with st.spinner("💭 Ava is listening..."):
            time.sleep(0.5)
        bot_msg = generate_with_groq(user_input, mood_context)
    except Exception as e:
        bot_msg = f"⚠️ Groq error: {str(e)}"

    # Add bot response (no emoji prefix)
    display_msg = bot_msg
    st.session_state.chat.append({"role": "assistant", "content": display_msg})
    with st.chat_message("assistant"):
        st.write(display_msg)
        # Speak if enabled and not already speaking
        # --- Minor adjustment: Ensure state check is robust ---
        if enable_voice and ELEVENLABS_API_KEY:
            # Double-check is_speaking state before starting
            if not st.session_state.get('is_speaking', False): # Use .get for safety
                 with st.spinner("🔊 Ava is speaking..."):
                     speak_with_elevenlabs(bot_msg, ELEVENLABS_API_KEY)
            else:
                 st.warning("Ava is still speaking. Please stop her current speech to hear this message.")

# ================================
# 🌼 Footer
# ================================
st.markdown("""
---
MindBloom 🌸 A safe space to feel.  
Not a replacement for therapy — just a kind companion.
""")
