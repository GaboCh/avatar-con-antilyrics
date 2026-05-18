from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Configuración de Groq
# Obtén tu API Key en: https://console.groq.com/
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "TU_API_KEY_AQUI")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

@app.route("/chat", methods=["POST"])
def chat():
    datos = request.json
    mensaje = datos.get("mensaje", "")
    modelo = datos.get("model", "llama-3.3-70b-versatile") # Modelo por defecto equilibrado

    if not mensaje:
        return jsonify({"error": "No se proporcionó mensaje"}), 400

    if GROQ_API_KEY == "TU_API_KEY_AQUI":
        return jsonify({"error": "API Key de Groq no configurada en backend_avatar/groq_service/app.py"}), 500

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Eres un experto en marketing de redes sociales. Generas títulos y descripciones virales."},
            {"role": "user", "content": mensaje}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return jsonify(response.json())
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error al conectar con Groq: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Puerto 5005 para no chocar con el llm_service original (5004)
    print(f"🚀 Servicio de Groq iniciado en el puerto 5005")
    app.run(port=5005, debug=True)
