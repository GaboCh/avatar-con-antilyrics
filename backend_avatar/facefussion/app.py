from flask import Flask, request, send_file, jsonify
import os
import shutil
import subprocess
import uuid

app = Flask(__name__)

# 📁 Rutas base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FACES = os.path.join(BASE_DIR, 'inputs', 'faces')
INPUT_VIDEOS = os.path.join(BASE_DIR, 'inputs', 'videos')
OUTPUT_VIDEOS = os.path.join(BASE_DIR, 'outputs', 'videos')

# 📁 Ruta donde está el .bat de FaceFusion
# Configura la variable de entorno PINOKIO_PATH o edita el archivo config_rutas.txt
_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_rutas.txt")
if os.path.exists(_config_file):
    with open(_config_file, "r") as _f:
        PINOKIO_PATH = _f.read().strip()
else:
    PINOKIO_PATH = os.environ.get("PINOKIO_PATH", r"D:\PINOKIO\api\facefusion-pinokio.git")
BAT_PATH = os.path.join(PINOKIO_PATH, "run_facefusion.bat")

# 🛠️ Crear carpetas necesarias si no existen
for path in [INPUT_FACES, INPUT_VIDEOS, OUTPUT_VIDEOS]:
    os.makedirs(path, exist_ok=True)
    print(f"🟢 Carpeta creada o ya existente: {path}")

@app.route('/swap', methods=['POST'])
def swap_face():
    # 📥 Validar archivos subidos
    face = request.files.get('face')
    video = request.files.get('video')
    if not face or not video:
        return jsonify({"error": "Debes subir 'face' y 'video'"}), 400

    # 🔐 Generar ID único
    uid = str(uuid.uuid4())

    # 📥 Guardar archivos en inputs
    face_path = os.path.join(INPUT_FACES, f'{uid}.jpg')
    video_path = os.path.join(INPUT_VIDEOS, f'{uid}.mp4')
    face.save(face_path)
    video.save(video_path)

    # 📤 Copiar archivos al entorno de ejecución de FaceFusion
    shutil.copy(face_path, os.path.join(PINOKIO_PATH, "foto_cara.jpg"))
    shutil.copy(video_path, os.path.join(PINOKIO_PATH, "video_prueba.mp4"))

    # ▶️ Ejecutar el batch
    print(f"🚀 Ejecutando FaceFusion con UID {uid}...")
    proc = subprocess.run(["run_facefusion.bat"], cwd=PINOKIO_PATH, shell=True)

    if proc.returncode != 0:
        return jsonify({"error": "Falló la ejecución del batch"}), 500

    # 📦 Verificar resultado
    generated_video = os.path.join(PINOKIO_PATH, "video_swap.mp4")
    if not os.path.exists(generated_video):
        return jsonify({"error": "No se generó el video de salida"}), 500

    # 📁 Mover resultado a outputs/videos
    final_output = os.path.join(OUTPUT_VIDEOS, f"{uid}.mp4")
    shutil.move(generated_video, final_output)

    # ✅ Retornar el archivo
    return send_file(final_output, as_attachment=True, download_name=f"{uid}.mp4")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100, debug=True, use_reloader=True)
