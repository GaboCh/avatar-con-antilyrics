from flask import Flask, request, jsonify, send_file
import requests
import json
import os
import tempfile
import time
from urllib.parse import urlparse

app = Flask(__name__)

# URL del servicio Gradio
GRADIO_BASE_URL = "http://127.0.0.1:7860"
GRADIO_GENERATE_URL = f"{GRADIO_BASE_URL}/gradio_api/call/generate_first"

# Voces disponibles
VOICES = {
    "dora": "🇪🇸 🚺 Dora",
    "alex": "🇪🇸 🚹 Alex", 
    "santa": "🇪🇸 🚹 Santa"
}

def validate_and_get_voice(voice_input):
    """Función helper para validar y obtener la voz"""
    if voice_input is None:
        return 'santa', VOICES['santa']
    
    # Si es una clave válida
    voice_key = voice_input.lower()
    if voice_key in VOICES:
        return voice_key, VOICES[voice_key]
    
    # Si ya es el valor completo (🇪🇸 🚹 Santa)
    for key, value in VOICES.items():
        if voice_input == value:
            return key, value
    
    # Si no es válido
    return None, None

@app.route('/generate', methods=['POST'])
def generate_audio():
    """Endpoint 1: Inicia la generación de audio y retorna el event_id"""
    try:
        # Obtener datos del request
        data = request.get_json()
        
        # Validar que tenemos los datos necesarios
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extraer parámetros
        text = data.get('text', '')
        voice_input = data.get('voice', 'santa')
        speed = data.get('speed', 0.95)
        format_type = data.get('format', 'MP3')
        
        # Validar texto
        if not text:
            return jsonify({"error": "Text is required"}), 400
        
        # Validar y obtener la voz
        voice_key, voice = validate_and_get_voice(voice_input)
        if voice_key is None:
            return jsonify({
                "error": f"Invalid voice '{voice_input}'. Available voices: {list(VOICES.keys())}",
                "available_voices": VOICES
            }), 400
        
        # Validar speed
        if not isinstance(speed, (int, float)) or speed <= 0 or speed > 2:
            return jsonify({"error": "Speed must be a number between 0.1 and 2.0"}), 400
        
        # Validar formato
        if format_type.upper() not in ['MP3', 'WAV']:
            return jsonify({"error": "Format must be MP3 or WAV"}), 400
        
        # Preparar el payload para Gradio
        gradio_payload = {
            "data": [text, voice, speed, format_type]
        }
        
        # Hacer la petición a Gradio
        response = requests.post(
            GRADIO_GENERATE_URL,
            headers={'Content-Type': 'application/json'},
            json=gradio_payload,
            timeout=30
        )
        
        # Verificar que la petición fue exitosa
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "event_id": result.get('event_id'),
                "status": "processing",
                "message": "Audio generation started",
                "parameters": {
                    "text": text,
                    "voice": voice,
                    "voice_key": voice_key,
                    "speed": speed,
                    "format": format_type
                }
            })
        else:
            return jsonify({
                "error": f"Gradio API returned status {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/get_path/<event_id>', methods=['GET'])
def get_file_path(event_id):
    """Endpoint 2: Obtiene la ruta del archivo usando el event_id"""
    try:
        # URL para obtener el estado
        status_url = f"{GRADIO_BASE_URL}/gradio_api/call/generate_first/{event_id}"
        
        # Hacer la petición a Gradio
        response = requests.get(status_url, timeout=30)
        
        if response.status_code == 200:
            response_text = response.text
            
            # Buscar la información del archivo en la respuesta
            if 'path' in response_text and 'url' in response_text:
                try:
                    # Intentar parsear como JSON
                    import re
                    
                    # Buscar el path
                    path_match = re.search(r'"path":\s*"([^"]+)"', response_text)
                    url_match = re.search(r'"url":\s*"([^"]+)"', response_text)
                    orig_name_match = re.search(r'"orig_name":\s*"([^"]+)"', response_text)
                    
                    if path_match and url_match:
                        file_path = path_match.group(1)
                        file_url = url_match.group(1)
                        orig_name = orig_name_match.group(1) if orig_name_match else None
                        
                        return jsonify({
                            "event_id": event_id,
                            "status": "completed",
                            "file_path": file_path,
                            "file_url": file_url,
                            "original_name": orig_name,
                            "message": "File ready for download"
                        })
                    else:
                        return jsonify({
                            "event_id": event_id,
                            "status": "processing",
                            "message": "File not ready yet"
                        }), 202
                        
                except Exception as e:
                    return jsonify({
                        "event_id": event_id,
                        "status": "error",
                        "error": f"Error parsing response: {str(e)}",
                        "raw_response": response_text
                    }), 500
            else:
                return jsonify({
                    "event_id": event_id,
                    "status": "processing",
                    "message": "File not ready yet"
                }), 202
        else:
            return jsonify({
                "error": f"Status check failed with status {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/download_from_url', methods=['POST'])
def download_from_gradio_url():
    """Endpoint 3: Descarga el archivo desde la URL de Gradio"""
    try:
        data = request.get_json()
        if not data or 'file_url' not in data:
            return jsonify({"error": "file_url is required"}), 400
        
        file_url = data['file_url']
        filename = data.get('filename', 'audio.mp3')
        
        # Descargar el archivo desde Gradio
        response = requests.get(file_url, timeout=60)
        
        if response.status_code == 200:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(response.content)
                tmp_file_path = tmp_file.name
            
            # Retornar el archivo
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='audio/mpeg'
            )
        else:
            return jsonify({
                "error": f"Failed to download file: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/generate_complete', methods=['POST'])
def generate_complete():
    """Endpoint 4: Servicio completo que consume los 3 endpoints anteriores"""
    try:
        # Obtener datos del request original
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validar la voz ANTES de empezar el proceso
        voice_input = data.get('voice', 'santa')
        voice_key, voice = validate_and_get_voice(voice_input)
        if voice_key is None:
            return jsonify({
                "error": f"Invalid voice '{voice_input}'. Available voices: {list(VOICES.keys())}",
                "available_voices": VOICES
            }), 400
        
        # Actualizar los datos con la voz validada
        data['voice'] = voice_key  # Usar la clave para consistencia
        
        # Paso 1: Generar audio
        print(f"Paso 1: Iniciando generación con voz {voice_key} ({voice})...")
        generate_response = requests.post(
            'http://localhost:5000/generate',
            headers={'Content-Type': 'application/json'},
            json=data,
            timeout=30
        )
        
        if generate_response.status_code != 200:
            return jsonify({
                "error": "Failed to start generation",
                "details": generate_response.text
            }), generate_response.status_code
        
        generate_result = generate_response.json()
        event_id = generate_result.get('event_id')
        
        if not event_id:
            return jsonify({"error": "No event_id received"}), 500
        
        print(f"Paso 1 completado. Event ID: {event_id}")
        
        # Paso 2: Esperar y obtener la ruta del archivo
        print("Paso 2: Esperando que el archivo esté listo...")
        max_attempts = 30
        file_info = None
        
        for attempt in range(max_attempts):
            time.sleep(1)
            
            path_response = requests.get(
                f'http://localhost:5000/get_path/{event_id}',
                timeout=10
            )
            
            if path_response.status_code == 200:
                file_info = path_response.json()
                if file_info.get('status') == 'completed':
                    print(f"Paso 2 completado. Archivo listo: {file_info.get('file_path')}")
                    break
            elif path_response.status_code != 202:
                return jsonify({
                    "error": "Failed to get file path",
                    "details": path_response.text
                }), path_response.status_code
        
        if not file_info or file_info.get('status') != 'completed':
            return jsonify({
                "error": "Timeout waiting for file generation",
                "event_id": event_id,
                "message": "Generation is taking longer than expected"
            }), 408
        
        # Paso 3: Descargar el archivo
        print("Paso 3: Descargando archivo...")
        download_payload = {
            "file_url": file_info.get('file_url'),
            "filename": file_info.get('original_name', f'audio_{voice_key}.mp3')
        }
        
        download_response = requests.post(
            'http://localhost:5000/download_from_url',
            headers={'Content-Type': 'application/json'},
            json=download_payload,
            timeout=60
        )
        
        if download_response.status_code == 200:
            print(f"Paso 3 completado. Descarga exitosa con voz {voice_key}.")
            # Crear archivo temporal con el contenido descargado
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(download_response.content)
                tmp_file_path = tmp_file.name
            
            # Retornar el archivo con nombre que incluye la voz
            filename = f"audio_{voice_key}_{int(time.time())}.mp3"
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='audio/mpeg'
            )
        else:
            return jsonify({
                "error": "Failed to download file",
                "details": download_response.text
            }), download_response.status_code
            
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Endpoint 5: Obtener las voces disponibles"""
    return jsonify({
        "available_voices": VOICES,
        "usage": "Use the key (dora, alex, santa) in the 'voice' parameter"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud"""
    return jsonify({"status": "healthy", "service": "TTS Proxy"})

@app.route('/', methods=['GET'])
def home():
    """Endpoint de documentación"""
    return jsonify({
        "message": "TTS Proxy Service - 5 Endpoints",
        "voices": VOICES,
        "endpoints": {
            "1": {
                "url": "/generate",
                "method": "POST",
                "description": "Inicia generación y retorna event_id"
            },
            "2": {
                "url": "/get_path/<event_id>",
                "method": "GET", 
                "description": "Obtiene la ruta del archivo generado"
            },
            "3": {
                "url": "/download_from_url",
                "method": "POST",
                "description": "Descarga archivo desde URL de Gradio"
            },
            "4": {
                "url": "/generate_complete",
                "method": "POST",
                "description": "Servicio completo: genera y descarga automáticamente"
            },
            "5": {
                "url": "/voices",
                "method": "GET",
                "description": "Lista las voces disponibles"
            },
            "6": {
                "url": "/health",
                "method": "GET",
                "description": "Verifica el estado del servicio"
            }
        },
        "workflows": {
            "manual": {
                "1": "POST /generate -> get event_id",
                "2": "GET /get_path/<event_id> -> get file_url",
                "3": "POST /download_from_url -> download file"
            },
            "automatic": {
                "1": "POST /generate_complete -> get file directly"
            }
        },
        "examples": {
            "generate_dora": {
                "url": "/generate",
                "method": "POST",
                "body": {
                    "text": "Hola, soy Dora",
                    "voice": "dora",
                    "speed": 1.0,
                    "format": "MP3"
                }
            },
            "generate_alex": {
                "url": "/generate",
                "method": "POST",
                "body": {
                    "text": "Hola, soy Alex",
                    "voice": "alex",
                    "speed": 0.9,
                    "format": "MP3"
                }
            },
            "generate_santa": {
                "url": "/generate",
                "method": "POST",
                "body": {
                    "text": "Ho ho ho, soy Santa",
                    "voice": "santa",
                    "speed": 0.8,
                    "format": "MP3"
                }
            },
            "complete_dora": {
                "url": "/generate_complete",
                "method": "POST",
                "body": {
                    "text": "Hola mundo con Dora",
                    "voice": "dora"
                }
            }
        }
    })
    
# PODCAST
    
@app.route("/generate_script", methods=["POST"])
def generate_script():
    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename.endswith(".txt"):
        return jsonify({"error": "Se requiere un archivo .txt"}), 400

    texto = archivo.read().decode("utf-8")

    # Paso 1: detectar los speakers únicos en orden de aparición
    import re
    pattern = re.compile(r"^(Dora|Alex|Santa):", re.MULTILINE)
    nombres_encontrados = pattern.findall(texto)
    
    # Obtener speakers únicos manteniendo el orden de primera aparición
    speakers_unicos = []
    for nombre in nombres_encontrados:
        if nombre not in speakers_unicos:
            speakers_unicos.append(nombre)
    
    print(f"🔍 Speakers únicos encontrados en orden: {speakers_unicos}")

    # Paso 2: NUEVA ESTRATEGIA - Compensar el desplazamiento
    # Basándome en tu output, parece que hay un desplazamiento de +2 posiciones
    # Dora (pos 0) usa voz en pos 2 (Santa)
    # Santa (pos 1) usa voz en pos 0 (Alex rotado)
    # Alex (pos 2) usa voz en pos 1 (Dora rotado)
    
    # Crear mapeo compensado
    voces_compensadas = []
    
    if len(speakers_unicos) >= 1:
        # Para que Dora use su propia voz, ponemos la voz de Dora en la posición que el sistema usará para Dora
        # Si Dora usa la posición 2, ponemos la voz de Dora en la posición 2
        pass
    
    # NUEVA ESTRATEGIA: Rotar las voces hacia la izquierda para compensar
    voces_originales = []
    for speaker in speakers_unicos:
        speaker_lower = speaker.lower()
        voz = VOICES.get(speaker_lower)
        if voz:
            voces_originales.append(voz)
    
    # Rotar las voces 1 posición hacia la derecha para compensar el desplazamiento
    if len(voces_originales) >= 2:
        # Rotar: [Dora, Santa, Alex] -> [Alex, Dora, Santa]
        voces_rotadas = [voces_originales[-1]] + voces_originales[:-1]
    else:
        voces_rotadas = voces_originales
    
    print(f"🔄 Voces originales: {voces_originales}")
    print(f"🔄 Voces rotadas: {voces_rotadas}")
    
    # Completar con Santa hasta 10
    while len(voces_rotadas) < 10:
        voces_rotadas.append(VOICES["santa"])
    
    voces_rotadas = voces_rotadas[:10]
    
    print(f"🎙️ Voces finales asignadas: {voces_rotadas}")

    payload = {
        "data": [
            texto,
            0.8,  # pausa
            1.0,  # velocidad
            "MP3"
        ] + voces_rotadas
    }

    try:
        r = requests.post(
            f"{GRADIO_BASE_URL}/gradio_api/call/generate_from_script_with_voices",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        if r.status_code != 200:
            return jsonify({"error": "Kokoro error", "detalle": r.text}), r.status_code

        result = r.json()
        event_id = result.get("event_id")
        
        print(f"✅ Event ID generado: {event_id}")
        
        return jsonify({
            "event_id": event_id,
            "speakers_detectados": speakers_unicos,
            "voces_originales": voces_originales,
            "voces_rotadas": voces_rotadas[:len(speakers_unicos)]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/generate_podcast_complete", methods=["POST"])
def generate_podcast_complete():
    """Genera un podcast completo a partir de un archivo .txt con diálogo"""

    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename.endswith(".txt"):
        return jsonify({"error": "Se requiere un archivo .txt"}), 400

    texto = archivo.read().decode("utf-8")

    # Paso 1: Obtener event_id desde /generate_script
    try:
        script_response = requests.post(
            "http://localhost:5000/generate_script",
            files={"archivo": ("guion.txt", texto)},
            timeout=30
        )
        if script_response.status_code != 200:
            return jsonify({"error": "Fallo al generar el event_id", "detalle": script_response.text}), 500

        script_json = script_response.json()
        event_id = script_json.get("event_id")

        if not event_id:
            return jsonify({"error": "Respuesta sin event_id"}), 500

        print(f"🟢 Paso 1 completado. Event ID: {event_id}")
    except Exception as e:
        return jsonify({"error": f"Error en generación inicial: {str(e)}"}), 500

    # Paso 2: Esperar a que esté listo el archivo desde /get_path/<event_id>
    file_info = None
    print("⏳ Paso 2: Esperando que el archivo esté listo...")
    for attempt in range(60):
        try:
            time.sleep(1)
            path_response = requests.get(f"http://localhost:5000/get_path/{event_id}", timeout=10)
            if path_response.status_code == 200:
                file_info = path_response.json()
                if file_info.get("status") == "completed":
                    print(f"✅ Archivo listo: {file_info.get('file_url')}")
                    break
            elif path_response.status_code != 202:
                return jsonify({"error": "Fallo en /get_path", "detalle": path_response.text}), 500
        except Exception as e:
            print(f"❌ Error en intento {attempt + 1}: {e}")
            continue

    if not file_info or file_info.get("status") != "completed":
        return jsonify({
            "error": "Timeout esperando el podcast",
            "event_id": event_id
        }), 408

    # Paso 3: Descargar archivo desde /download_from_url
    try:
        print("📥 Paso 3: Descargando podcast...")
        download_payload = {
            "file_url": file_info.get("file_url"),
            "filename": file_info.get("original_name", "podcast.mp3")
        }

        download_response = requests.post(
            "http://localhost:5000/download_from_url",
            headers={"Content-Type": "application/json"},
            json=download_payload,
            timeout=60
        )

        if download_response.status_code != 200:
            return jsonify({"error": "Error al descargar", "detalle": download_response.text}), 500

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(download_response.content)
            path = tmp.name

        print("🎧 Podcast descargado y listo para enviar")
        return send_file(
            path,
            download_name=f"podcast_{int(time.time())}.mp3",
            as_attachment=True,
            mimetype="audio/mpeg"
        )
    except Exception as e:
        return jsonify({"error": f"Error al descargar podcast: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)