import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
import os
import subprocess
import time

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
# 🎨 Page Config & Warm Theme
# ================================
st.set_page_config(page_title="🌸 Ava", layout="centered")


# ================================
# 🌸 Title & Welcome Message
# ================================
st.title("🌸 Ava - Your Compassionate Companion")

st.markdown("""
<div class="welcome">
Hi there, I'm Ava 💖<br>
I'm here to listen — without judgment, without rush.<br>
Whatever you're feeling, it's okay. You're safe here.
</div>
""", unsafe_allow_html=True)

# ================================
# 🧠 Initialize Session State
# ================================
if "chat" not in st.session_state:
    st.session_state.chat = []
if "mood_logs" not in st.session_state:
    st.session_state.mood_logs = []
if "mood_history" not in st.session_state:
    st.session_state.mood_history = []  # Full emotional timeline

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
            # Rebuild mood_history from logs
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
st.sidebar.markdown("### 🌿 How are you today?")
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
    
    # Save to file
    os.makedirs("data", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(st.session_state.mood_logs, f, indent=2)
    
    st.sidebar.success(f"Mood logged: {selected_mood}")

# Show mood history
if st.session_state.mood_logs:
    st.sidebar.subheader("Your Mood Journal")
    df = pd.DataFrame(st.session_state.mood_logs)
    st.sidebar.dataframe(df.tail(7), use_container_width=True)

# Little love note in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("💬 You're not alone.")
st.sidebar.markdown("🌼 Breathe. Share. Be held.")

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

    # Detect mood from input
    current_mood = detect_mood(user_input)
    
    # Add to mood history
    st.session_state.mood_history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mood": current_mood
    })

    # Build emotional context for Ava
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

    # Generate bot response
    try:
        # Use ONLY the user input + context (no system prompt — handled by Modelfile)
        full_prompt = f"[INST] {mood_context}\n\nUser: {user_input} [/INST]"

        with st.spinner("💭 Ava is listening..."):
            time.sleep(0.5)

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "ava",  # ← Make sure you built this with `ollama create ava -f Modelfile`
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.75,
                    "top_p": 0.9,
                    "num_ctx": 8192
                }
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

# ================================
# 🌼 Footer
# ================================
st.markdown("""
<div class="footer">
    MindBloom 🌸 A safe space to feel.<br>
    Not a replacement for therapy — just a kind companion.
</div>
""", unsafe_allow_html=True)