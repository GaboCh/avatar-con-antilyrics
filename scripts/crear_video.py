import os
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

# Configuración
nombre_base = "ya_no_te_hago_falta"
CARPETA_IMAGENES = "./imagenes"
CARPETA_AUDIOS = "./audios"
CARPETA_PROYECTOS = "./proyectos"

ruta_audio = os.path.join(CARPETA_AUDIOS, f"{nombre_base}.mp3")
ruta_salida_video = os.path.join(CARPETA_PROYECTOS, f"{nombre_base}.mp4")

# Verificar existencia del archivo de audio
if not os.path.exists(ruta_audio):
    print("❌ Falta el archivo de audio.")
    exit()

# Ordenar imágenes
imagenes = sorted([
    os.path.join(CARPETA_IMAGENES, f) 
    for f in os.listdir(CARPETA_IMAGENES) 
    if f.startswith(nombre_base) and f.endswith(".png")
])

if not imagenes:
    print("❌ No se encontraron imágenes.")
    exit()

# Cargar audio y calcular duración por imagen
audio = AudioFileClip(ruta_audio)
duracion_total = audio.duration
duracion_por_imagen = duracion_total / len(imagenes)

print(f"Duración total del audio: {duracion_total:.2f} segundos")
print(f"Duración por imagen: {duracion_por_imagen:.2f} segundos")
print(f"Número de imágenes: {len(imagenes)}")

# Crear clips de imágenes
clips = []
for idx, img in enumerate(imagenes):
    print(f"Procesando imagen {idx + 1}/{len(imagenes)}: {os.path.basename(img)}")
    
    # Crear clip de imagen
    img_clip = ImageClip(img).with_duration(duracion_por_imagen).resized(height=1280).with_position("center")
    clips.append(img_clip)

# Unir todos y exportar
print("\nCreando video final...")
video_final = concatenate_videoclips(clips).with_audio(audio)

# Crear carpeta proyectos si no existe
os.makedirs(CARPETA_PROYECTOS, exist_ok=True)

video_final.write_videofile(
    ruta_salida_video,
    fps=24,
    codec="libx264",
    audio_codec="aac",
    temp_audiofile='temp-audio.m4a',
    remove_temp=True
)

print(f"✅ Video generado: {ruta_salida_video}")