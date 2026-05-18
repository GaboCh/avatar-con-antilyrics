import os
import requests
import base64
import time

# Configuración
ENDPOINT_CHAT = "http://127.0.0.1:5004/chat"
ENDPOINT_IMAGEN = "http://127.0.0.1:5005/generar_imagen"
ENDPOINT_AUDIO = "http://127.0.0.1:5000/generate_podcast_complete"
CARPETA_AUDIOS = "./audios"
CARPETA_SRT = "./subtitulos"

CARPETA_GUIONES = "./guiones"
CARPETA_PROMPTS = "./prompts_generados"
CARPETA_IMAGENES = "./imagenes"

# Lora que se inyecta automáticamente en cada prompt
LORA = "<lora:Hyper-FLUX.1-dev-8steps-lora:0.12>"
ESTILO = "estilo Studio Ghibli"
ATMOSFERA = "atmósfera de tranquilidad y de familia, paz interior, espiritualidad o inspiración emocional"

# Elegimos el guion a procesar
nombre_archivo = "ya_no_te_hago_falta.txt"  # Cambialo por el nombre del guion que tengas
ruta_guion = os.path.join(CARPETA_GUIONES, nombre_archivo)

# Leer el guion
with open(ruta_guion, "r", encoding="utf-8") as f:
    texto_guion = f.read()

# Armamos el mensaje para la IA pidiendo 10 prompts
# mensaje_ia = (
#     "A partir del siguiente texto que representa el significado o la letra de una canción, "
#     "imagina una historia breve que represente visualmente ese mensaje, con uno o más personajes.\n"
#     "Divide esa historia en 10 escenas visuales, como si fuera un cortometraje animado o un videoclip ilustrado con narrativa emocional.\n"
#     "Cada escena debe tener continuidad con la anterior y reflejar una parte clave de la historia, transmitiendo emociones profundas (amor, tristeza, libertad, nostalgia, etc.).\n"
#     "Describe cada escena con un prompt detallado en español para generar una imagen artística.\n"
#     "Usa un estilo visual similar al de Studio Ghibli o ilustración emocional, con luz cálida, composición armónica, y paisajes naturales o poéticos.\n"
#     "IMPORTANTE: Devuelve solo la lista de 10 prompts, uno por línea, sin encabezados, numeración ni explicaciones. No incluyas verbos de movimiento (como 'camina', 'se aleja', 'lentamente', 'mira', etc.).\n"
#     f"Texto de referencia:\n{texto_guion}\n\n"
# )
mensaje_ia = (
    "A partir del siguiente texto que representa el significado o la letra de una canción, "
    "imagina una historia breve que represente visualmente ese mensaje, con uno o más personajes.\n"
    "Divide esa historia en 10 escenas visuales, como si fuera un cortometraje animado o un videoclip ilustrado con narrativa emocional.\n"
    "Cada escena debe tener continuidad con la anterior y reflejar una parte clave de la historia, transmitiendo emociones profundas (amor, tristeza, libertad, nostalgia, etc.).\n"
    "Describe cada escena con un prompt detallado en español para generar una imagen artística.\n"
    "Usa un estilo visual similar al de Studio Ghibli o ilustración emocional, con luz cálida, composición armónica, y paisajes naturales o poéticos.\n"
    "IMPORTANTE: Devuelve solo la lista de 10 prompts, uno por línea, sin encabezados, numeración ni explicaciones.\n"
    "No incluyas verbos de movimiento (como 'camina', 'se aleja', 'lentamente', 'mira', etc.).\n"
    "Evita metáforas abstractas o escenas simbólicas difíciles de representar físicamente. Describe solo elementos visuales claros, concretos y posibles de ilustrar sin ambigüedad.\n"
    "Cuando describas personas, asegúrate de que tengan posturas naturales, proporciones humanas coherentes y expresiones comprensibles. Evita detalles anatómicos confusos o poses imposibles.\n"
    "Evita escenas con espejos, reflejos, sombras dobles o versiones múltiples del mismo personaje, ya que pueden causar errores visuales.\n\n"
    "IMPORTANTE: Devuelve solo la lista de 10 prompts, uno por línea, sin encabezados, numeración ni explicaciones.\n"
    f"Texto de referencia:\n{texto_guion}\n\n"
)

# Payload para la IA
payload_ia = {"mensaje": mensaje_ia}

# Enviar al endpoint de chat
response = requests.post(ENDPOINT_CHAT, json=payload_ia)

if response.status_code == 200:
    contenido = response.json()

    try:
        respuesta_ia = contenido["choices"][0]["message"]["content"]
        print("\nPrompts generados por la IA:\n")
        print(respuesta_ia)

        # Guardamos los prompts
        nombre_prompts = os.path.splitext(nombre_archivo)[0] + "_prompts.txt"
        ruta_salida = os.path.join(CARPETA_PROMPTS, nombre_prompts)

        with open(ruta_salida, "w", encoding="utf-8") as f:
            f.write(respuesta_ia)

        print(f"\nPrompts guardados en {ruta_salida}")

        # Leer los prompts y generar imágenes
        prompts = [linea.strip() for linea in respuesta_ia.split("\n") if linea.strip()]
        print(f"\nGenerando {len(prompts)} imágenes...\n")

        for idx, prompt in enumerate(prompts, start=1):
            prompt_final = (
                f"{prompt}, {ESTILO}, {ATMOSFERA} {LORA}"  # Inyectamos el Lora aquí
            )
            payload_img = {"prompt": prompt_final}

            try:
                resp_img = requests.post(ENDPOINT_IMAGEN, json=payload_img)
                if resp_img.status_code == 200:
                    r_img = resp_img.json()
                    if r_img.get("status") == "ok":
                        imagen_base64 = r_img["imagen_base64"]
                        nombre_imagen = (
                            f"{os.path.splitext(nombre_prompts)[0]}_{idx}.png"
                        )
                        ruta_imagen = os.path.join(CARPETA_IMAGENES, nombre_imagen)

                        with open(ruta_imagen, "wb") as f:
                            f.write(base64.b64decode(imagen_base64))

                        print(f"✅ Imagen {idx} generada: {ruta_imagen}")
                    else:
                        print(
                            f"⚠️ Error al generar imagen {idx}: {r_img.get('mensaje')}"
                        )
                else:
                    print(f"⚠️ Error HTTP generando imagen {idx}: {resp_img.text}")

            except Exception as e:
                print(f"⚠️ Error generando imagen {idx}: {e}")

            time.sleep(1)  # Pausa entre peticiones

    except Exception as e:
        print("Error procesando la respuesta de la IA:", e)

else:
    print("Error al comunicar con el endpoint de chat:", response.text)

# === GENERAR AUDIO CON EL GUION ===

try:
    print("\n🎤 Enviando el guión al servicio de audio...")

    with open(ruta_guion, "rb") as f:
        files = {"archivo": (nombre_archivo, f)}
        response_audio = requests.post(ENDPOINT_AUDIO, files=files, timeout=120)

        if response_audio.status_code == 200:
            # Guardar audio
            nombre_audio = os.path.splitext(nombre_archivo)[0] + ".mp3"
            ruta_audio = os.path.join(CARPETA_AUDIOS, nombre_audio)

            with open(ruta_audio, "wb") as f:
                f.write(response_audio.content)

            print(f"✅ Audio generado: {ruta_audio}")

        else:
            print(
                f"❌ Error HTTP generando audio: {response_audio.status_code} - {response_audio.text}"
            )

except Exception as e:
    print(f"❌ Error al generar el audio: {e}")

# Esperar a que el archivo .mp3 exista
import pathlib

nombre_audio = os.path.splitext(nombre_archivo)[0] + ".mp3"
ruta_audio = os.path.join(CARPETA_AUDIOS, nombre_audio)

print(f"\n🕐 Esperando que se cree el archivo de audio: {ruta_audio}")

esperado = pathlib.Path(ruta_audio)
intentos = 0
while not esperado.exists() and intentos < 30:
    time.sleep(1)
    intentos += 1

if not esperado.exists():
    print("❌ No se encontró el archivo de audio después de esperar.")
else:
    print("✅ Archivo de audio encontrado, iniciando transcripción...")

    with open(ruta_audio, "rb") as f:
        files = {"file": (nombre_audio, f, "audio/mpeg")}
        try:
            response = requests.post("http://127.0.0.1:5007/transcribir", files=files)
            if response.status_code == 200:
                ruta_salida_srt = os.path.join(
                    CARPETA_SRT, os.path.splitext(nombre_audio)[0] + ".srt"
                )
                with open(ruta_salida_srt, "wb") as out:
                    out.write(response.content)
                print(f"✅ Transcripción guardada como: {ruta_salida_srt}")
            else:
                print(
                    f"❌ Error HTTP al transcribir: {response.status_code} - {response.text}"
                )
        except Exception as e:
            print(f"❌ Error al hacer la solicitud de transcripción: {e}")
