from flask import Flask, request, jsonify
import requests
import base64
import time

app = Flask(__name__)

# Configuración de Forge
FORGE_URL = "http://127.0.0.1:7861"


@app.route("/generar_imagen", methods=["POST"])
def generar_imagen():
    datos = request.json
    prompt = datos.get("prompt", "")

    if not prompt:
        return jsonify({"error": "Prompt vacío"}), 400

    # Payload quemado, solo se inserta el prompt dinámicamente flux1-kontext-dev-Q2_K.gguf flux1-kontext-dev-Q4_K_M
    payload = {
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, ugly, bad anatomy, distorted, poorly drawn, disfigured, extra fingers, text artifacts, watermark",
        "steps": 15,
        "sampler_name": "Euler",
        "scheduler": "Simple",
        "cfg_scale": 1,
        "distilled_cfg_scale": 3.5,
        "seed": -1,
        "width": 720,
        "height": 1024,
        "restore_faces": True,
        "tiling": False,
        "override_settings": {"sd_model_checkpoint": "flux1-kontext-dev-Q2_K"},
        "send_images": True,
        "save_images": False,
    }

    try:
        response = requests.post(f"{FORGE_URL}/sdapi/v1/txt2img", json=payload)
        r = response.json()
        print(f"🔍 Respuesta de Forge: {r}")

        if "images" in r:
            imagen_base64 = r["images"][0]
            return jsonify(
                {
                    "status": "ok",
                    "mensaje": "Imagen generada exitosamente.",
                    "imagen_base64": imagen_base64,
                }
            )

        return jsonify({"status": "error", "mensaje": "No se generó imagen."}), 500

    except Exception as e:
        print(f"⚠️ Error al comunicarse con Forge: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5005)
