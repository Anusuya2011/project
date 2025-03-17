from flask import Flask, render_template, request, jsonify, send_file
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from googletrans import Translator
import os
import uuid
import json
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
HISTORY_FILE = "history.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

translator = Translator()

# Function to save history
def save_history(filename):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    
    history.insert(0, {"name": filename, "date": datetime.now().strftime("%Y-%m-%d")})
    history = history[:10]  # Keep only last 10 records

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

# Function to get history
def get_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/audio-to-text", methods=["GET", "POST"])
def audio_to_text():
    return render_template("audio_file_to_text.html")

@app.route("/speech-recognition")
def speech_recognition():
    return render_template("speech_recognition.html")

@app.route("/convert-audio", methods=["POST"])
def convert_audio():
    if "audioFile" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    audio_file = request.files["audioFile"]
    if audio_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    audio_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
    audio_file.save(audio_path)

    start_time = int(request.form.get("start_time", 0))
    end_time = int(request.form.get("end_time", 0))
    if start_time or end_time:
        audio = AudioSegment.from_file(audio_path)
        trimmed_audio = audio[start_time * 1000:end_time * 1000]
        trimmed_audio_path = os.path.join(UPLOAD_FOLDER, f"trimmed_{audio_file.filename}")
        trimmed_audio.export(trimmed_audio_path, format="wav")
        audio_path = trimmed_audio_path

    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data)
        save_history(audio_file.filename)  # Save to history
        return jsonify({"converted_text": text})
    except sr.UnknownValueError:
        return jsonify({"error": "Could not understand the audio"}), 400
    except sr.RequestError:
        return jsonify({"error": "Error connecting to speech recognition service"}), 500

@app.route("/translate-text", methods=["POST"])
def translate_text():
    data = request.get_json()
    text = data.get("text", "")
    target_lang = data.get("target_lang", "en")

    try:
        translated = translator.translate(text, dest=target_lang)
        translated_text = translated.text
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"translated_text": translated_text})

@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    data = request.get_json()
    text = data.get("text", "")
    lang = data.get("lang", "en")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    tts = gTTS(text=text, lang=lang, slow=False)
    speech_file = os.path.join(UPLOAD_FOLDER, f"speech_{uuid.uuid4()}.mp3")
    tts.save(speech_file)

    return send_file(speech_file, mimetype="audio/mp3")

@app.route("/download-text", methods=["POST"])
def download_text():
    data = request.get_json()
    text = data.get("text", "")
    filename = data.get("filename", "text.txt")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    temp_file = os.path.join(UPLOAD_FOLDER, filename)
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(text)

    return send_file(temp_file, as_attachment=True)

@app.route("/get-history", methods=["GET"])
def get_history_route():
    return jsonify({"history": get_history()})

if __name__ == "__main__":
    app.run(debug=True)