
import os
import hmac
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DEVICE_TOKEN = os.environ["DEVICE_TOKEN"]

MODEL = "gemini-3.5-flash-lite"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/" + MODEL + ":generateContent"
)


@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "message": "ESP32 Backend Ready"
    })


@app.post("/ask")
def ask():
    token = request.headers.get("X-Device-Token", "")

    if not hmac.compare_digest(token, DEVICE_TOKEN):
        return jsonify({"error": "Unauthorized"}), 401

    if request.content_length and request.content_length > 2048:
        return jsonify({"error": "Request too large"}), 413

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    question = data.get("question", "")

    if not isinstance(question, str):
        return jsonify({"error": "Invalid question"}), 400

    question = question.strip()

    if not question or len(question) > 500:
        return jsonify({"error": "Question must be 1-500 characters"}), 400

    payload = {
        "contents": [{
            "parts": [{"text": question}]
        }],
        "generationConfig": {
            "maxOutputTokens": 300
        }
    }

    try:
        response = requests.post(
            GEMINI_URL,
            headers={
                "x-goog-api-key": GEMINI_API_KEY
            },
            json=payload,
            timeout=45
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Google API unavailable",
                "google_status": response.status_code
            }), 502

        result = response.json()

        parts = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )

        answer = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        )

        return jsonify({
            "answer": answer or "No answer returned",
            "model": MODEL
        })

    except requests.RequestException:
        return jsonify({
            "error": "Google connection failed"
        }), 502
