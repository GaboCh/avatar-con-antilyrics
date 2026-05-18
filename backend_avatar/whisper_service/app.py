import os
import time
import requests
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

WHISPER_API = "http://127.0.0.1:8000"
SRT_DIR = "subtitulos"
os.makedirs(SRT_DIR, exist_ok=True)

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def generar_srt(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, item in enumerate(data, 1):
            start = format_time(item["start"])
            end = format_time(item["end"])
            text = item["text"].strip()
            f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

@app.route('/transcribir', methods=['POST'])
def transcribir():
    if 'file' not in request.files:
        return jsonify({"error": "Archivo no encontrado"}), 400

    audio = request.files['file']
    filename = audio.filename
    print(f"📥 Recibido archivo: {filename}")
    audio.save(filename)

    try:
        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'audio/mpeg')}
            params = {
                "model_size": "large-v2",
                "is_translate": "false",
                "beam_size": 5,
                "log_prob_threshold": -1,
                "no_speech_threshold": 0.6,
                "compute_type": "float16",
                "best_of": 5,
                "patience": 1,
                "condition_on_previous_text": "true",
                "prompt_reset_on_temperature": 0.5,
                "temperature": 0,
                "compression_ratio_threshold": 2.4,
                "length_penalty": 1,
                "repetition_penalty": 1,
                "no_repeat_ngram_size": 0,
                "suppress_blank": "true",
                "max_initial_timestamp": 1,
                "word_timestamps": "false",
                "prepend_punctuations": "\"'“¿([{-",
                "append_punctuations": "\"'.。,，!！?？:：”)]}、",
                "chunk_length": 30,
                "language_detection_threshold": 0.5,
                "language_detection_segments": 1,
                "batch_size": 24,
                "enable_offload": "true",
                "vad_filter": "false",
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 2000,
                "speech_pad_ms": 400,
                "is_separate_bgm": "false",
                "uvr_model_size": "UVR-MDX-NET-Inst_HQ_4",
                "uvr_device": "cuda",
                "segment_size": 256,
                "save_file": "false",
                "is_diarize": "false",
                "diarization_device": "cuda"
            }

            transcribe = requests.post(f"{WHISPER_API}/transcription", files=files, params=params)
            print(f"🔁 Respuesta transcripción status: {transcribe.status_code}")
            if transcribe.status_code != 201:
                return jsonify({"error": "Error al transcribir", "details": transcribe.text}), 500

            identifier = transcribe.json().get("identifier")
            print(f"🆔 Identificador obtenido: {identifier}")

        # Estimar duración aproximada (tamaño del archivo en segundos)
        duracion_aprox = os.path.getsize(filename) / (128 * 1024) * 60  # Asume 128 kbps MP3
        intervalo, intentos = estimar_polling(duracion_aprox)

        # Calcular ETA
        eta_total = intervalo * intentos
        eta_min = eta_total // 60
        eta_sec = eta_total % 60
        print(f"⏱️ Estimación: {duracion_aprox:.2f}s → intervalo {intervalo}s × {intentos} intentos")
        print(f"🕒 Máximo tiempo estimado de espera: {int(eta_min)}m {int(eta_sec)}s")

        # Polling
        for _ in range(intentos):
            task = requests.get(f"{WHISPER_API}/task/{identifier}")
            data = task.json()
            if data.get("status") == "completed":
                print("✅ Transcripción completada. Generando SRT...")
                result = data.get("result")
                srt_path = os.path.join(SRT_DIR, f"{os.path.splitext(filename)[0]}.srt")
                generar_srt(result, srt_path)
                print(f"📝 Archivo SRT generado: {srt_path}")
                return send_file(srt_path, as_attachment=True)

            elif data.get("status") == "failed":
                return jsonify({"error": "Error en la transcripción"}), 500

            time.sleep(intervalo)

        return jsonify({"error": "Timeout esperando la transcripción"}), 504


    finally:
        if os.path.exists(filename):
            os.remove(filename)

def estimar_polling(duracion_segundos):
    """
    Retorna tupla (intervalo_en_segundos, intentos_maximos)
    según duración del audio.
    """
    if duracion_segundos <= 300:      # <= 5 minutos
        return 3, 40                  # hasta 2 minutos de espera
    elif duracion_segundos <= 900:    # <= 15 minutos
        return 5, 60                  # hasta 5 minutos
    elif duracion_segundos <= 1800:   # <= 30 minutos
        return 7, 70                  # ~8 minutos
    else:                             # > 30 minutos
        return 10, 90                 # hasta 15 minutos

if __name__ == '__main__':
    app.run(port=5007, debug=True)
