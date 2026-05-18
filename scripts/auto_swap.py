import os
import glob,math
import subprocess
import time
import random
from pathlib import Path


"""
========================================
AUTO-DESCARGA + FACE SWAP: SECUENCIA
========================================
1) crear_estructura_carpetas() 
   - Asegura /swap/modelos/<modelo>, /swap/videos_originales, /swap/videos_finales, /swap/url.
   - Crea /swap/url/url.txt de ejemplo si no existe.

2) mostrar_contenido_archivo()
   - Muestra el contenido actual de /swap/url/url.txt para verificar las URLs.

3) leer_urls_desde_archivo()
   - Lee y valida las líneas de url.txt. Devuelve solo URLs de Instagram.

4) descargar_desde_archivo()
   - Llama internamente a leer_urls_desde_archivo().
   - Descarga con yt-dlp cada URL en /swap/videos_originales usando pausas aleatorias.

5) realizar_face_swap()
   - Recorre /swap/videos_originales.
   - Envía cada video junto con la cara del modelo al endpoint Flask `/swap`.
   - Guarda el resultado en /swap/videos_finales como <modelo><n>.mp4.

Entrypoint:
- main() ejecuta 1→2→3/4 y luego llama a realizar_face_swap().
========================================
Requisitos:
- yt-dlp instalado (`pip install yt-dlp`)
- Cookies válidas si la cuenta o el recurso lo exige:
  /swap/cookies/www.instagram.com_cookies.txt
- Servicio Flask de FaceFusion corriendo en http://127.0.0.1:5100/swap
========================================
"""
# === CONFIGURACIÓN DE RUTAS ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SWAP_DIR = os.path.join(BASE_DIR, 'swap')

# Archivo donde pondrás las URLs
URL_FILE = os.path.join(SWAP_DIR, 'url', 'url.txt')

def crear_estructura_carpetas():
    """
    Crear todas las carpetas necesarias incluyendo la carpeta url
    """
    carpetas = [
        os.path.join(SWAP_DIR, 'modelos', 'alexa'),
        os.path.join(SWAP_DIR, 'videos_originales'),
        os.path.join(SWAP_DIR, 'videos_finales'),
        os.path.join(SWAP_DIR, 'url')  # Nueva carpeta para URLs
    ]
    
    for carpeta in carpetas:
        os.makedirs(carpeta, exist_ok=True)
        print(f"🟢 Carpeta creada: {carpeta}")
    
    # Crear archivo url.txt si no existe
    if not os.path.exists(URL_FILE):
        with open(URL_FILE, 'w', encoding='utf-8') as f:
            f.write('# Pega aquí las URLs de Instagram, una por línea\n')
            f.write('# Ejemplo:\n')
            f.write('# https://www.instagram.com/p/ABC123/\n')
            f.write('# https://www.instagram.com/reel/DEF456/\n\n')
        print(f"📄 Archivo creado: {URL_FILE}")
        print("💡 Edita este archivo y agrega las URLs de Instagram")

def leer_urls_desde_archivo():
    """
    Leer URLs desde el archivo url.txt
    """
    if not os.path.exists(URL_FILE):
        print(f"❌ No se encontró el archivo: {URL_FILE}")
        return []
    
    try:
        with open(URL_FILE, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
        
        # Filtrar URLs válidas (ignorar comentarios y líneas vacías)
        urls = []
        for i, linea in enumerate(lineas, 1):
            linea = linea.strip()
            
            # Ignorar líneas vacías y comentarios
            if not linea or linea.startswith('#'):
                continue
            
            # Validar que sea una URL de Instagram
            if linea.startswith('https://www.instagram.com/'):
                urls.append(linea)
                print(f"✅ URL {len(urls)}: {linea}")
            else:
                print(f"⚠️ Línea {i} ignorada (no es URL válida): {linea}")
        
        return urls
        
    except Exception as e:
        print(f"❌ Error leyendo archivo {URL_FILE}: {e}")
        return []

def descargar_video_individual(url, numero):
    """
    Descargar un video individual usando yt-dlp
    """
    output_dir = os.path.join(SWAP_DIR, 'videos_originales')
    
    # Comando yt-dlp optimizado
    cmd = [
        'yt-dlp',
        url,
        '--format', 'mp4/best',
        '--output', f'{output_dir}/video_{numero:02d}_%(id)s.%(ext)s',
        '--no-warnings',
        '--no-playlist',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '--extractor-retries', '3',
        '--socket-timeout', '30',
        '--cookies', os.path.join(SWAP_DIR, 'cookies', 'www.instagram.com_cookies.txt'),

    ]
    
    try:
        print(f"📥 Descargando video {numero:02d}...")
        print(f"🔗 URL: {url}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Video {numero:02d} descargado exitosamente")
            return True
        else:
            print(f"❌ Error en video {numero:02d}:")
            print(f"   {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout en video {numero:02d} (5 minutos)")
        return False
    except FileNotFoundError:
        print("❌ yt-dlp no está instalado.")
        print("💡 Instala con: pip install yt-dlp")
        return False
    except Exception as e:
        print(f"❌ Error inesperado en video {numero:02d}: {e}")
        return False

def descargar_desde_archivo():
    """
    Leer URLs del archivo y descargar todos los videos automáticamente
    """
    print(f"\n📂 Leyendo URLs desde: {URL_FILE}")
    print("-" * 60)
    
    urls = leer_urls_desde_archivo()
    
    if not urls:
        print("❌ No se encontraron URLs válidas en el archivo.")
        print(f"💡 Edita el archivo: {URL_FILE}")
        print("💡 Agrega URLs de Instagram, una por línea")
        return
    
    print(f"\n🎬 SE DESCARGARÁN {len(urls)} VIDEOS AUTOMÁTICAMENTE")
    print("=" * 60)
    
    # Espera inicial aleatoria para evitar detección
    espera_inicial = random.uniform(10, 20)
    print(f"⏳ Esperando {espera_inicial:.1f} segundos antes de comenzar...")
    print("💡 (Esto ayuda a evitar bloqueos automáticos)")
    time.sleep(espera_inicial)
    
    exitosos = 0
    errores = 0
    
    for i, url in enumerate(urls, 1):
        print(f"\n📹 VIDEO {i}/{len(urls)}")
        print("-" * 40)
        
        # Descargar
        if descargar_video_individual(url, i):
            exitosos += 1
        else:
            errores += 1
        
        # Espera entre descargas (más tiempo para evitar bloqueos)
        if i < len(urls):
            tiempo_espera = random.uniform(15, 30)  # Aumenté el tiempo
            print(f"⏳ Esperando {tiempo_espera:.1f} segundos antes del siguiente...")
            print("💤 (Pausa para evitar detección automática)")
            time.sleep(tiempo_espera)
    
    # Resumen final
    print(f"\n{'='*60}")
    print(f"🎯 DESCARGA COMPLETADA AUTOMÁTICAMENTE")
    print(f"✅ Exitosos: {exitosos}")
    print(f"❌ Errores: {errores}")
    print(f"📁 Videos guardados en: {os.path.join(SWAP_DIR, 'videos_originales')}")
    print(f"📄 URLs procesadas desde: {URL_FILE}")
    print(f"{'='*60}")

def mostrar_contenido_archivo():
    """
    Mostrar el contenido actual del archivo url.txt
    """
    if os.path.exists(URL_FILE):
        print(f"\n📄 Contenido actual de {URL_FILE}:")
        print("-" * 50)
        try:
            with open(URL_FILE, 'r', encoding='utf-8') as f:
                contenido = f.read()
                if contenido.strip():
                    print(contenido)
                else:
                    print("(Archivo vacío)")
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
        print("-" * 50)

def main():
    print("🚀 DESCARGADOR AUTOMÁTICO DE VIDEOS DESDE URL.TXT")
    print("=" * 60)
    
    # Crear estructura de carpetas
    crear_estructura_carpetas()
    
    # Mostrar contenido actual del archivo
    mostrar_contenido_archivo()
    
    # Verificar si hay URLs para descargar
    urls = leer_urls_desde_archivo()
    
    if urls:
        print(f"\n🎯 INICIANDO DESCARGA AUTOMÁTICA DE {len(urls)} VIDEOS")
        print("💡 No se requiere confirmación - proceso automático")
        print("⚠️ Presiona Ctrl+C si quieres cancelar")
        
        # Pequeña pausa para que el usuario pueda cancelar si quiere
        try:
            time.sleep(3)
            descargar_desde_archivo()
        except KeyboardInterrupt:
            print("\n❌ Descarga cancelada por el usuario")
    else:
        print(f"\n⚠️ No hay URLs para descargar.")
        print(f"📝 Edita el archivo: {URL_FILE}")
        print(f"📝 Agrega URLs de Instagram, una por línea")
        print(f"🔄 Luego ejecuta este script nuevamente")

def realizar_face_swap(): 
    import requests

    modelo = 'alexa'
    face_path = os.path.join(SWAP_DIR, 'modelos', modelo, 'face.jpeg')
    originales_dir = os.path.join(SWAP_DIR, 'videos_originales')
    finales_dir = os.path.join(SWAP_DIR, 'videos_finales')
    swap_endpoint = 'http://127.0.0.1:5100/swap'

    if not os.path.exists(face_path):
        print(f"❌ No se encontró la imagen de la cara en: {face_path}")
        return

    videos = [f for f in os.listdir(originales_dir) if f.lower().endswith(('.mp4', '.mov'))]
    if not videos:
        print(f"❌ No se encontraron videos en: {originales_dir}")
        return

    for idx, video_file in enumerate(videos, start=1):
        video_path = os.path.join(originales_dir, video_file)
        print(f"\n🔄 Procesando {video_file} ({idx}/{len(videos)})...")

        try:
            with open(face_path, 'rb') as face_file, open(video_path, 'rb') as vid_file:
                files = {
                    'face': face_file,
                    'video': vid_file
                }
                response = requests.post(swap_endpoint, files=files)

            if response.status_code == 200:
                output_path = os.path.join(finales_dir, f'{modelo}{idx}.mp4')
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Video generado: {output_path}")
            else:
                print(f"❌ Error del servicio: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ Error procesando {video_file}: {e}")

def postprocesar_variantes_sin_aspecto(crf=21, preset="medium", seed=None):
    """
    Aplica una pila de transformaciones sutiles a cada video para maximizar su
    originalidad y evitar la detección de contenido duplicado.
    """
    import os
    import subprocess
    import random
    import glob
    
    # Si no se proporciona una semilla, usa el tiempo actual para máxima aleatoriedad
    if seed is None:
        random.seed(time.time())
    else:
        random.seed(seed)

    # --- Lógica de búsqueda de FFmpeg (la que ya funciona) ---
    ffmpeg_cmd, ffprobe_cmd = None, None
    print("🔍 Buscando FFmpeg local dentro del entorno virtual...")
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        ffprobe_path = ffmpeg_cmd.replace("ffmpeg-win64-v4.2.2.exe", "ffprobe.exe").replace("ffmpeg.exe", "ffprobe.exe")
        if os.path.exists(ffmpeg_cmd) and os.path.exists(ffprobe_path):
            ffprobe_cmd = ffprobe_path
            print(f"✅ FFmpeg encontrado en: {ffmpeg_cmd}")
        else:
            ffmpeg_cmd = None
            print("❌ No se encontró ffprobe.exe junto a ffmpeg.exe")
    except Exception as e:
        print(f"❌ Error al localizar FFmpeg: {e}")

    if not ffmpeg_cmd or not ffprobe_cmd:
        print("\n❌ ERROR FATAL: No se pudo encontrar FFmpeg local. Saltando postprocesamiento.")
        return
        
    # --- Configuración de directorios ---
    finales_dir = os.path.join(SWAP_DIR, "videos_finales")
    out_dir = os.path.join(SWAP_DIR, "videos_finales_procesados")
    os.makedirs(out_dir, exist_ok=True)

    videos = sorted(glob.glob(os.path.join(finales_dir, "*.mp4")))
    if not videos:
        print(f"⚠️ No hay MP4 en {finales_dir} para postprocesar.")
        return

    print(f"🎬 Iniciando postprocesamiento AVANZADO de {len(videos)} videos...")

    # ===== BANCO DE TRANSFORMACIONES SUTILES =====
    # (Elegiremos una de cada categoría para cada video)

    recetas_geometricas = [
        {"name": "rot_izq", "vf": "rotate=-0.005"},
        {"name": "rot_der", "vf": "rotate=0.005"},
        {"name": "zoom_ligero", "vf": "scale=iw*1.01:ih*1.01,crop=iw/1.01:ih/1.01"},
        {"name": "flip_h", "vf": "hflip"} # CUIDADO: Voltea horizontalmente, puede arruinar texto
    ]

    recetas_color = [
        {"name": "contraste_alto", "vf": "eq=contrast=1.01:brightness=-0.005"},
        {"name": "contraste_bajo", "vf": "eq=contrast=0.99:brightness=0.005"},
        {"name": "saturacion_alta", "vf": "eq=saturation=1.05"},
        {"name": "calido", "vf": "colorbalance=rs=0.02"},
        {"name": "frio", "vf": "colorbalance=bs=0.02"}
    ]

    recetas_audio = [
        {"name": "pitch_up", "af": "asetrate=44100*1.01,aresample=44100"},
        {"name": "pitch_down", "af": "asetrate=44100*0.99,aresample=44100"},
        {"name": "tempo_rapido", "af": "atempo=1.01"},
        {"name": "tempo_lento", "af": "atempo=0.99"}
    ]

    # ===== PROCESAMIENTO DE VIDEOS =====
    for i, src_path in enumerate(videos):
        # 1. Elige una transformación aleatoria de cada categoría
        geo = random.choice(recetas_geometricas)
        color = random.choice(recetas_color)
        audio = random.choice(recetas_audio)
        
        # 2. Combina los filtros de video y audio
        filtros_vf = [
            "setsar=1", # Normalizar aspect ratio
            geo['vf'], 
            color['vf']
        ]
        vf_chain = ",".join(filtros_vf)
        af_chain = audio['af']

        # 3. Define nombres y rutas
        base_name = os.path.splitext(os.path.basename(src_path))[0]
        recipe_name = f"{geo['name']}_{color['name']}_{audio['name']}"
        dst_path = os.path.join(out_dir, f"{base_name}_{recipe_name}.mp4")

        print(f"🔄 Procesando {i+1}/{len(videos)}: {os.path.basename(src_path)} → [{recipe_name}]")

        # 4. Construye y ejecuta el comando FFmpeg
        try:
            # Comando base
            cmd = [
                ffmpeg_cmd, "-y", "-i", src_path,
                "-vf", vf_chain,
                "-af", af_chain,
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                dst_path
            ]
            
            # El recorte estructural se puede añadir, pero es más complejo.
            # Por ahora, esta combinación es muy potente.
            
            # Usamos DEVNULL para una salida más limpia en la consola
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✅ Video generado: {os.path.basename(dst_path)}")

        except subprocess.CalledProcessError:
            print(f"❌ Error de FFmpeg procesando {os.path.basename(src_path)}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")

    print(f"🎯 Postprocesamiento AVANZADO completado. Videos en: {out_dir}")


if __name__ == '__main__':
    main()
    realizar_face_swap()
    # tras realizar_face_swap()
    postprocesar_variantes_sin_aspecto(crf=20, preset="medium", seed=123)

