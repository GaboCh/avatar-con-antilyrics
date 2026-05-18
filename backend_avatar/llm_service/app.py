from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# IP y puerto de LLMStudio (podés guardarlo en .env si querés)
LLMSTUDIO_URL = "http://192.168.100.2:1234/v1/chat/completions"

@app.route("/chat", methods=["POST"])
def chat():
    datos = request.json
    mensaje = datos.get("mensaje", "")

    payload = {
        "messages": [
            {"role": "system", "content": "Eres un asistente útil."},
            {"role": "user", "content": mensaje}
        ]
    }

    try:
        respuesta = requests.post(LLMSTUDIO_URL, json=payload)
        respuesta.raise_for_status()
        contenido = respuesta.json()

        return jsonify(contenido)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5004)
