# Ava – Compassionate Companion (Streamlit)

A simple Streamlit app that provides an empathetic, privacy-friendly chat companion. Text responses are generated via Groq's chat completions API. Optional voice replies use ElevenLabs TTS.

## Features

- Groq API for fast, high-quality responses
- Mood logging and sidebar journal
- Optional ElevenLabs voice replies with a visible Stop Speaking button

## Requirements

- Python 3.10+
- A Groq API key
- (Optional) An ElevenLabs API key if you enable voice

## Setup

1. Create and activate a virtual environment (recommended)

   - Windows (PowerShell):
     `powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
     `
   - macOS/Linux:
     `bash
python3 -m venv .venv
source .venv/bin/activate
     `

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure secrets:
   - Copy the example file and fill in your keys
     ```bash
     mkdir -p .streamlit
     copy .streamlit\secrets.example.toml .streamlit\secrets.toml # Windows
     ```

# or

cp .streamlit/secrets.example.toml .streamlit/secrets.toml # macOS/Linux

````

- Edit `.streamlit/secrets.toml`:
  `toml
groq_api_key = "YOUR_GROQ_API_KEY"
groq_model = "llama3-8b-8192"        # optional
elevenlabs_api_key = "YOUR_ELEVENLABS_API_KEY"  # optional
     `

4. Run the app:
   ```bash
   streamlit run app.py
````

## Notes

- Data files (mood logs) are saved under `data/` and the folder is created automatically at runtime.
- The Stop Speaking button appears while voice playback is active and disappears when playback ends or you stop it.
- To change the Groq model, set `groq_model` in `.streamlit/secrets.toml`.
- Keep `.streamlit/secrets.toml` out of version control (see `.gitignore`).

## Troubleshooting

- Groq errors: Ensure `groq_api_key` is valid and network access is available.
- Voice issues: Ensure `elevenlabs_api_key` is set; check sound output and that `pygame` can initialize the mixer.
