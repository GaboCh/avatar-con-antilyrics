import os
import glob
import subprocess
import time
import random
import sys
from pathlib import Path
import shutil
import gradio as gr
import configparser
import publicador_automatico
# =========== INICIO DEL CÓDIGO ORIGINAL MODIFICADO ===========
# Se ha adaptado para que funcione con Gradio y redirija la salida.

# --- CONFIGURACIÓN DE RUTAS ---
# MODIFICACIÓN: Se ajusta la ruta base para que sea portable.
# El script está en .../GUI/scripts/
# Las carpetas de trabajo deben crearse en .../GUI/proyectos_gui/

# 1. Obtiene el directorio del script actual (.../GUI/scripts)
script_dir = os.path.abspath(os.path.dirname(__file__))
# 2. Sube un nivel para llegar al directorio padre (.../GUI)
gui_dir = os.path.dirname(script_dir)
# 3. Establece el directorio base de trabajo en la carpeta deseada (.../GUI/proyectos_gui)
BASE_DIR = os.path.join(gui_dir, 'proyectos_gui')

# A partir de aquí, todas las rutas se construirán dentro de .../GUI/proyectos_gui/
SWAP_DIR = os.path.join(BASE_DIR, 'swap')

# Archivo donde se guardan las URLs
URL_FILE = os.path.join(SWAP_DIR, 'url', 'url.txt')

# --- CONSOLA VIRTUAL PARA GRADIO ---
# Redirigimos los prints para que se muestren en la UI
class GradioConsole:
    def __init__(self):
        self.buffer = ""
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

    def write(self, text):
        self.buffer += text
        self.old_stdout.write(text) # <-- AÑADIDO: Escribe en la terminal original
        self.old_stdout.flush() 
        # No usamos el stdout original en este contexto
        
    def flush(self):
        pass # No es necesario para nuestro buffer

    def get_buffer(self):
        return self.buffer
    
    def clear_buffer(self):
        self.buffer = ""

    def start_redirect(self):
        sys.stdout = self
        sys.stderr = self

    def stop_redirect(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

console = GradioConsole()

# --- NUEVA FUNCIÓN PARA DETECTAR MODELOS DE CARAS ---
def obtener_modelos_disponibles():
    """Escanea el directorio de modelos y devuelve una lista de los disponibles."""
    modelos_dir = os.path.join(SWAP_DIR, 'modelos')
    if not os.path.exists(modelos_dir):
        return []
    
    modelos_validos = []
    for nombre_modelo in os.listdir(modelos_dir):
        ruta_modelo = os.path.join(modelos_dir, nombre_modelo)
        ruta_cara = os.path.join(ruta_modelo, 'face.jpeg')
        if os.path.isdir(ruta_modelo) and os.path.exists(ruta_cara):
            modelos_validos.append(nombre_modelo)
            
    # Imprimimos en la consola del terminal, no en la de Gradio, ya que esto se ejecuta al inicio.
    print(f"Modelos de cara encontrados: {modelos_validos}")
    return sorted(modelos_validos)


# --- FUNCIONES ADAPTADAS ---

def crear_estructura_carpetas():
    """Crear todas las carpetas necesarias según la nueva lógica."""
    console.clear_buffer()
    console.start_redirect()
    
    print("📂 Creando estructura de carpetas...")
    os.makedirs(BASE_DIR, exist_ok=True)
    print(f"🟢 Directorio base verificado: {BASE_DIR}")

    # Carpetas dentro de 'proyectos_gui/swap'
    carpetas_swap = [
        os.path.join(SWAP_DIR, 'modelos', 'alexa'), # Se crea 'alexa' como ejemplo
        os.path.join(SWAP_DIR, 'videos_originales'),
        os.path.join(SWAP_DIR, 'videos_finales'),
        os.path.join(SWAP_DIR, 'videos_finales_procesados'),
        os.path.join(SWAP_DIR, 'url'),
        os.path.join(SWAP_DIR, 'cookies'),
    ]
    
    for carpeta in carpetas_swap:
        os.makedirs(carpeta, exist_ok=True)
        print(f"🟢 Carpeta SWAP creada/verificada: {carpeta}")
    
    # Carpeta final de Anticopyright dentro de 'anticopryng'
    anticopyright_output_dir = os.path.join(gui_dir, 'anticopryng', 'videos_anticopyright')
    os.makedirs(anticopyright_output_dir, exist_ok=True)
    print(f"🟢 Carpeta ANTICOPYRIGHT creada/verificada: {anticopyright_output_dir}")

    if not os.path.exists(URL_FILE):
        with open(URL_FILE, 'w', encoding='utf-8') as f:
            f.write('# Pega aquí las URLs de Instagram, una por línea\n')
        print(f"📄 Archivo creado: {URL_FILE}")
        
    cookies_file = os.path.join(SWAP_DIR, 'cookies', 'www.instagram.com_cookies.txt')
    if not os.path.exists(cookies_file):
        with open(cookies_file, 'w', encoding='utf-8') as f:
            f.write('# Pega aquí el contenido de tus cookies de Instagram\n')
        print(f"🍪 Archivo de cookies creado: {cookies_file}")

    print("\n✅ Estructura de carpetas lista.")
    output = console.get_buffer()
    console.stop_redirect()
    return output

def leer_urls_desde_archivo(log_func=print):
    """Leer URLs desde el archivo url.txt."""
    if not os.path.exists(URL_FILE):
        log_func(f"❌ No se encontró el archivo: {URL_FILE}")
        return []
    
    try:
        with open(URL_FILE, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
        
        urls = []
        for i, linea in enumerate(lineas, 1):
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            if linea.startswith('https://www.instagram.com/'):
                urls.append(linea)
                log_func(f"✅ URL {len(urls)}: {linea}")
            else:
                log_func(f"⚠️ Línea {i} ignorada (no es URL válida): {linea}")
        return urls
    except Exception as e:
        log_func(f"❌ Error leyendo archivo {URL_FILE}: {e}")
        return []

def descargar_video_individual(url, numero, log_func=print):
    """Descargar un video individual usando yt-dlp."""
    output_dir = os.path.join(SWAP_DIR, 'videos_originales')
    cmd = [
        'yt-dlp', url, '--format', 'mp4/best',
        '--output', f'{output_dir}/video_{numero:02d}_%(id)s.%(ext)s',
        '--no-warnings', '--no-playlist',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '--add-header', 'Accept-Language:en-US,en;q=0.9,es;q=0.8',
        '--add-header', 'Referer:https://www.instagram.com/',
        '--extractor-retries', '5', '--socket-timeout', '30',
        '--sleep-interval', '3', '--max-sleep-interval', '8',
        '--cookies', os.path.join(SWAP_DIR, 'cookies', 'www.instagram.com_cookies.txt'),
    ]
    
    try:
        log_func(f"📥 Descargando video {numero:02d}...\n🔗 URL: {url}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8')
        
        if result.returncode == 0:
            log_func(f"✅ Video {numero:02d} descargado exitosamente")
            return True
        else:
            log_func(f"❌ Error en video {numero:02d}:\n   {result.stderr.strip()}")
            return False
    except Exception as e:
        log_func(f"❌ Error inesperado en video {numero:02d}: {e}")
        return False

def descargar_desde_archivo_gradio():
    """Función de descarga para ser llamada por Gradio."""
    console.clear_buffer()
    console.start_redirect()
    
    log_func = print
    
    log_func(f"📂 Leyendo URLs desde: {URL_FILE}")
    log_func("-" * 60)
    
    urls = leer_urls_desde_archivo(log_func)
    
    if not urls:
        log_func("❌ No se encontraron URLs válidas en el archivo.")
        output = console.get_buffer()
        console.stop_redirect()
        return output

    log_func(f"🎬 SE DESCARGARÁN {len(urls)} VIDEOS")
    log_func("=" * 60)
    
    exitosos, errores = 0, 0
    for i, url in enumerate(urls, 1):
        log_func(f"\n📹 VIDEO {i}/{len(urls)}")
        log_func("-" * 40)
        
        if descargar_video_individual(url, i, log_func):
            exitosos += 1
        else:
            errores += 1
        
        if i < len(urls):
            tiempo_espera = random.uniform(5, 10)
            log_func(f"⏳ Esperando {tiempo_espera:.1f} segundos...")
            time.sleep(tiempo_espera)
            
    log_func(f"\n{'='*60}\n🎯 DESCARGA COMPLETADA")
    log_func(f"✅ Exitosos: {exitosos}\n❌ Errores: {errores}")
    log_func(f"📁 Videos guardados en: {os.path.join(SWAP_DIR, 'videos_originales')}")
    
    output = console.get_buffer()
    console.stop_redirect()
    return output

# --- FUNCIÓN DE FACE SWAP MODIFICADA ---
# Ahora acepta una lista de modelos seleccionados desde la UI.
def realizar_face_swap_gradio(modelos_seleccionados):
    """Función de Face Swap para Gradio que usa una selección aleatoria de modelos."""
    console.clear_buffer()
    console.start_redirect()
    log_func = print

    if not modelos_seleccionados:
        log_func("❌ Error: Debes seleccionar al menos un modelo de cara para procesar.")
        log_func("💡 Ve a la pestaña 'Procesar Videos' y marca una o más casillas.")
        output = console.get_buffer()
        console.stop_redirect()
        return output
    
    log_func(f"👥 Modelos seleccionados para el proceso: {', '.join(modelos_seleccionados)}")
    
    try:
        import requests
    except ImportError:
        log_func("❌ Error: La librería 'requests' no está instalada. Por favor, ejecuta: pip install requests")
        output = console.get_buffer()
        console.stop_redirect()
        return output

    originales_dir = os.path.join(SWAP_DIR, 'videos_originales')
    finales_dir = os.path.join(SWAP_DIR, 'videos_finales')
    swap_endpoint = 'http://127.0.0.1:5100/swap'

    log_func("\n🔄 Iniciando proceso de Face Swap aleatorio...")

    videos = [f for f in os.listdir(originales_dir) if f.lower().endswith(('.mp4', '.mov'))]
    if not videos:
        log_func(f"❌ No se encontraron videos en: {originales_dir}")
        log_func("💡 Primero descarga algunos videos usando la pestaña 'Descargar'.")
        output = console.get_buffer()
        console.stop_redirect()
        return output

    for idx, video_file in enumerate(videos, start=1):
        # ¡Magia! Elegimos un modelo al azar de la lista para CADA video.
        modelo_elegido = random.choice(modelos_seleccionados)
        video_path = os.path.join(originales_dir, video_file)
        face_path = os.path.join(SWAP_DIR, 'modelos', modelo_elegido, 'face.jpeg')

        log_func(f"\n🔄 Procesando {video_file} ({idx}/{len(videos)}) -> Usando cara de: '{modelo_elegido}'")

        if not os.path.exists(face_path):
            log_func(f"❌ ¡ATENCIÓN! No se encontró la imagen de la cara para '{modelo_elegido}' en: {face_path}")
            log_func("   Saltando este video.")
            continue # Pasa al siguiente video

        try:
            with open(face_path, 'rb') as face_file, open(video_path, 'rb') as vid_file:
                files = {'face': face_file, 'video': vid_file}
                response = requests.post(swap_endpoint, files=files, timeout=300)

            if response.status_code == 200:
                # Nombre de archivo más descriptivo
                nombre_base_video = Path(video_file).stem
                output_path = os.path.join(finales_dir, f'{modelo_elegido}_{nombre_base_video}.mp4')
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                log_func(f"✅ Video generado: {Path(output_path).name}")
            else:
                log_func(f"❌ Error del servicio: {response.status_code}\n{response.text}")
        except requests.exceptions.ConnectionError:
            log_func(f"❌ Error de conexión con el servidor de FaceFusion.")
            log_func(f"💡 Asegúrate de que el servicio está corriendo en {swap_endpoint}")
            break
        except Exception as e:
            log_func(f"❌ Error procesando {video_file}: {e}")

    log_func("\n🎯 Proceso de Face Swap finalizado.")
    output = console.get_buffer()
    console.stop_redirect()
    return output

def postprocesar_variantes_gradio(crf, preset, seed_str):
    """Función de postprocesamiento para Gradio."""
    console.clear_buffer()
    console.start_redirect()
    
    log_func = print
    seed = int(seed_str) if seed_str.isdigit() else None

    log_func("✨ Iniciando post-procesamiento AVANZADO...")

    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        if not os.path.exists(ffmpeg_cmd):
            raise FileNotFoundError
        log_func(f"✅ FFmpeg encontrado en: {ffmpeg_cmd}")
    except (ImportError, FileNotFoundError):
        log_func("❌ ERROR FATAL: No se pudo encontrar FFmpeg local.")
        log_func("💡 Instala imageio-ffmpeg: pip install imageio-ffmpeg")
        output = console.get_buffer()
        console.stop_redirect()
        return output

    finales_dir = os.path.join(SWAP_DIR, "videos_finales")
    out_dir = os.path.join(SWAP_DIR, "videos_finales_procesados")
    os.makedirs(out_dir, exist_ok=True)

    videos = sorted(glob.glob(os.path.join(finales_dir, "*.mp4")))
    if not videos:
        log_func(f"⚠️ No hay videos en {finales_dir} para postprocesar.")
        output = console.get_buffer()
        console.stop_redirect()
        return output
    
    log_func(f"🎬 Encontrados {len(videos)} videos para procesar.")

    if seed is None:
        random.seed(time.time())
        log_func("🌱 Usando semilla aleatoria (basada en el tiempo)")
    else:
        random.seed(seed)
        log_func(f"🌱 Usando semilla fija: {seed}")

    recetas_geometricas = [
        {"name": "rot_izq", "vf": "rotate=-0.005"}, {"name": "rot_der", "vf": "rotate=0.005"},
        {"name": "zoom_ligero", "vf": "scale=iw*1.01:ih*1.01,crop=iw/1.01:ih/1.01"}, {"name": "flip_h", "vf": "hflip"}
    ]
    recetas_color = [
        {"name": "contraste_alto", "vf": "eq=contrast=1.01:brightness=-0.005"},
        {"name": "contraste_bajo", "vf": "eq=contrast=0.99:brightness=0.005"},
        {"name": "saturacion_alta", "vf": "eq=saturation=1.05"}, {"name": "calido", "vf": "colorbalance=rs=0.02"},
        {"name": "frio", "vf": "colorbalance=bs=0.02"}
    ]
    recetas_audio = [
        {"name": "pitch_up", "af": "asetrate=44100*1.01,aresample=44100"},
        {"name": "pitch_down", "af": "asetrate=44100*0.99,aresample=44100"},
        {"name": "tempo_rapido", "af": "atempo=1.01"}, {"name": "tempo_lento", "af": "atempo=0.99"}
    ]

    for i, src_path in enumerate(videos):
        geo, color, audio = random.choice(recetas_geometricas), random.choice(recetas_color), random.choice(recetas_audio)
        vf_chain = f"setsar=1,{geo['vf']},{color['vf']}"
        af_chain = audio['af']
        base_name = Path(src_path).stem
        recipe_name = f"{geo['name']}_{color['name']}_{audio['name']}"
        dst_path = os.path.join(out_dir, f"{base_name}_{recipe_name}.mp4")

        log_func(f"\n🔄 Procesando {i+1}/{len(videos)}: {Path(src_path).name} → [{recipe_name}]")
        
        try:
            cmd = [
                ffmpeg_cmd, "-y", "-i", src_path, "-vf", vf_chain, "-af", af_chain,
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_func(f"✅ Video generado: {Path(dst_path).name}")
        except Exception as e:
            log_func(f"❌ Error de FFmpeg: {e}")

    log_func(f"\n🎯 Postprocesamiento completado. Videos en: {out_dir}")
    output = console.get_buffer()
    console.stop_redirect()
    return output

def limpiar_carpetas_videos_gradio(limpiar_originales, limpiar_finales, limpiar_procesados, limpiar_anticopyright):
    """Elimina el contenido de las carpetas de videos seleccionadas con la nueva estructura."""
    console.clear_buffer()
    console.start_redirect()
    log_func = print

    log_func("🗑️ Iniciando proceso de limpieza...")
    
    anticopyright_dir = os.path.join(gui_dir, 'anticopryng', 'videos_anticopyright')

    carpetas_a_limpiar = {
        "Videos Originales": (os.path.join(SWAP_DIR, 'videos_originales'), limpiar_originales),
        "Videos Finales (FaceSwap)": (os.path.join(SWAP_DIR, 'videos_finales'), limpiar_finales),
        "Videos Procesados": (os.path.join(SWAP_DIR, 'videos_finales_procesados'), limpiar_procesados),
        "Videos Anticopyright": (anticopyright_dir, limpiar_anticopyright)
    }

    total_eliminados = 0
    for nombre, (ruta, debe_limpiar) in carpetas_a_limpiar.items():
        if not debe_limpiar:
            log_func(f"\n⏭️ Omitiendo limpieza de: {nombre}")
            continue

        log_func(f"\n🧹 Limpiando carpeta: {nombre} ({ruta})")
        if not os.path.exists(ruta):
            log_func("⚠️ La carpeta no existe, no hay nada que limpiar.")
            continue

        archivos = glob.glob(os.path.join(ruta, '*'))
        if not archivos:
            log_func("✅ La carpeta ya está vacía.")
            continue
        
        count = 0
        for archivo in archivos:
            try:
                if os.path.isfile(archivo) or os.path.islink(archivo):
                    os.unlink(archivo)
                    count += 1
                elif os.path.isdir(archivo):
                    shutil.rmtree(archivo)
                    count += 1
            except Exception as e:
                log_func(f"❌ No se pudo eliminar {archivo}. Razón: {e}")
        
        log_func(f"👍 Se eliminaron {count} archivos/carpetas de {nombre}.")
        total_eliminados += count

    log_func(f"\n{'='*60}\n🎯 LIMPIEZA COMPLETADA")
    log_func(f"🗑️ Total de archivos/carpetas eliminados: {total_eliminados}")
    
    output = console.get_buffer()
    console.stop_redirect()
    return output

def iniciar_anticopyright_gradio(num_ciclos):
    """Orquesta la ejecución del proceso anticopyright con el nuevo flujo de carpetas."""
    console.clear_buffer()
    console.start_redirect()
    log_func = print

    anticopyright_scripts_dir = os.path.join(gui_dir, 'anticopryng')
    app_video_script = os.path.join(anticopyright_scripts_dir, 'app_video.py')
    input_dir = os.path.join(SWAP_DIR, 'videos_finales_procesados')
    output_dir_final = os.path.join(anticopyright_scripts_dir, 'videos_anticopyright')
    os.makedirs(output_dir_final, exist_ok=True)
    work_dir = os.path.join(anticopyright_scripts_dir, 'temp_work')
    work_input_dir = os.path.join(work_dir, 'videos_finales')
    work_output_dir = os.path.join(work_dir, 'videos_finales_procesados')

    log_func("🛡️ Iniciando Proceso Anti-Copyright (Flujo Directo)...")
    log_func(f"Ruta de Scripts: {anticopyright_scripts_dir}")
    log_func(f"Leyendo videos de: {input_dir}")
    log_func(f"Guardando resultados en: {output_dir_final}")

    if not os.path.exists(app_video_script):
        log_func(f"❌ ERROR FATAL: No se encontró el script 'app_video.py'.")
        output = console.get_buffer()
        console.stop_redirect()
        return output
        
    videos_a_procesar = sorted(glob.glob(os.path.join(input_dir, "*.mp4")))
    if not videos_a_procesar:
        log_func(f"⚠️ No se encontraron videos en '{input_dir}' para procesar.")
        output = console.get_buffer()
        console.stop_redirect()
        return output

    log_func(f"🎬 Encontrados {len(videos_a_procesar)} videos para procesar.")
    log_func("="*60)

    for i, video_path in enumerate(videos_a_procesar, 1):
        log_func(f"\n🔄 Procesando video {i}/{len(videos_a_procesar)}: {os.path.basename(video_path)}")
        
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_input_dir)
        os.makedirs(work_output_dir)

        shutil.copy(video_path, work_input_dir)
        log_func(f"   -> Copiado a taller temporal en 'anticopryng/temp_work'.")

        comando = [
            sys.executable, app_video_script,
            work_input_dir, work_output_dir, str(num_ciclos)
        ]
        
        try:
            resultado = subprocess.run(
                comando, check=True, capture_output=True, text=True,
                encoding='utf-8', errors='ignore'
            )
            log_func(f"   -> Proceso finalizado.")

            archivos_resultado = glob.glob(os.path.join(work_input_dir, "*.mp4"))
            if archivos_resultado:
                resultado_final_path = archivos_resultado[0]
                shutil.move(resultado_final_path, os.path.join(output_dir_final, os.path.basename(resultado_final_path)))
                log_func(f"   ✅ Resultado movido a: {output_dir_final}")
            else:
                log_func(f"   ❌ ¡ERROR! No se encontró el archivo final en el taller.")

        except subprocess.CalledProcessError as e:
            log_func(f"   ❌ ERROR FATAL al ejecutar el subproceso.")
            if e.stderr:
                log_func(f"   Mensaje de error: {e.stderr.strip()}")
        
        shutil.rmtree(work_dir)

    log_func(f"\n{'*'*60}\n*** PROCESO ANTICOPYRIGHT COMPLETADO ***")
    log_func(f"Los videos finales están en: {output_dir_final}")
    log_func(f"{'*'*60}")

    output = console.get_buffer()
    console.stop_redirect()
    return output
# --- FUNCIÓN "ORQUESTADORA" FINAL Y REAL ---
def iniciar_publicacion_automatica_gradio(videos_seleccionados, prompt_ia, fb_page_id, fb_token):
    """
    Función puente que recoge todo de la UI (incluyendo credenciales) y llama al orquestador real.
    """
    console.clear_buffer(); console.start_redirect()
    log_func = print

    # Verificación de que el usuario ha seleccionado al menos un video.
    if not videos_seleccionados or videos_seleccionados == ["No hay videos listos para publicar..."]:
        log_func("❌ No has seleccionado ningún video para publicar.")
        output = console.get_buffer(); console.stop_redirect(); return output

    # Verificación de que el usuario ha introducido las credenciales de Facebook.
    if not all([fb_page_id, fb_token]):
        log_func("❌ Error: Faltan el ID de Página o el Token de Facebook.")
        log_func("   -> Ve a la sección 'Configuración de Publicación' en esta misma pestaña, introduce tus datos y haz clic en 'Guardar'.")
        output = console.get_buffer(); console.stop_redirect(); return output

    # --- LLAMADA REAL AL "CEREBRO" ---
    # Ahora llamamos a la función principal de nuestro otro archivo, pasándole todo lo que necesita.
    publicador_automatico.procesar_y_publicar_lote(
        videos_seleccionados=videos_seleccionados, 
        prompt_ia=prompt_ia,
        log_func=log_func,
        gui_dir=gui_dir,
        fb_page_id=fb_page_id,
        fb_access_token=fb_token
    )
    
    output = console.get_buffer(); console.stop_redirect(); return output

# =========== INTERFAZ DE GRADIO ===========

def get_url_content():
    """Lee y devuelve el contenido del archivo de URLs."""
    if os.path.exists(URL_FILE):
        with open(URL_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    return "# El archivo url.txt no existe aún. Créalo con el botón de 'Crear Carpetas'."

def save_url_content(new_content):
    """Guarda el nuevo contenido en el archivo de URLs."""
    try:
        with open(URL_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return "✅ Archivo url.txt guardado."
    except Exception as e:
        return f"❌ Error al guardar: {e}"
# --- NUEVA FUNCIÓN AUXILIAR PARA LA PESTAÑA DE PUBLICACIÓN ---

def obtener_videos_finales():
    """Busca videos en la carpeta de salida de anticopyright para mostrarlos en la UI."""
    # Construye la ruta a la carpeta donde se guardan los videos listos para publicar
    anticopyright_dir = os.path.join(gui_dir, 'anticopryng', 'videos_anticopyright')
    
    if not os.path.exists(anticopyright_dir):
        return ["La carpeta de videos finales no existe..."]
    
    # Busca todos los archivos .mp4 en esa carpeta
    videos = sorted(glob.glob(os.path.join(anticopyright_dir, "*.mp4")))
    
    # Si se encuentran videos, devuelve solo sus nombres. Si no, un mensaje.
    if videos:
        return [os.path.basename(v) for v in videos]
    else:
        return ["No hay videos listos para publicar..."]

# --- NUEVAS FUNCIONES PARA MANEJAR EL ARCHIVO config.ini DESDE LA PANTALLA ---
def cargar_configuracion_facebook():
    """Carga la configuración de Facebook desde config.ini para la Pestaña 6."""
    config = configparser.ConfigParser()
    config_file = 'config.ini' # El nombre del archivo que crearemos
    
    if not os.path.exists(config_file):
        return "", "" # Devuelve campos vacíos si el archivo no existe
    
    config.read(config_file)
    page_id = config.get('FACEBOOK', 'page_id', fallback="")
    access_token = config.get('FACEBOOK', 'access_token', fallback="")
    return page_id, access_token

def guardar_configuracion_facebook(page_id, access_token):
    """Guarda las credenciales de Facebook de la Pestaña 6 en config.ini."""
    config = configparser.ConfigParser()
    config['FACEBOOK'] = {
        'page_id': page_id,
        'access_token': access_token
    }
    
    try:
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        return "✅ Configuración de Facebook guardada con éxito en config.ini."
    except Exception as e:
        return f"❌ Error al guardar el archivo config.ini: {e}"
# --- Construcción de la UI ---
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 Auto-Downloader, Swap & Processing UI")
    
    output_console = gr.Textbox(
        label="📄 Consola de Salida", lines=15, autoscroll=True,
        interactive=False
    )

    with gr.Tabs():
        with gr.TabItem("1. Configuración y URLs"):
            gr.Markdown("### Paso 1: Prepara el entorno y las URLs")
            btn_crear_carpetas = gr.Button("📁 Crear Estructura de Carpetas", variant="secondary")
            
            gr.Markdown("### Paso 2: Gestiona las URLs a descargar")
            url_editor = gr.Textbox(
                value=get_url_content, label="📝 Contenido de url.txt", lines=10,
                placeholder="Pega aquí las URLs de Instagram, una por línea..."
            )
            with gr.Row():
                btn_refresh_urls = gr.Button("🔄 Refrescar", variant="secondary")
                btn_save_urls = gr.Button("💾 Guardar Cambios en url.txt", variant="primary")
                
        with gr.TabItem("2. Descargar Videos"):
            gr.Markdown("### Paso 3: Descargar los videos desde las URLs")
            gr.Markdown("Pulsa el botón para iniciar la descarga automática usando `yt-dlp`.")
            btn_descargar = gr.Button("🚀 Iniciar Descarga Automática", variant="primary")
            
        # --- SECCIÓN DE LA INTERFAZ MODIFICADA ---
        with gr.TabItem("3. Procesar Videos"):
            gr.Markdown("### Paso 4: Realizar Face Swap")
            gr.Markdown(
                "Selecciona uno o más modelos de la lista. Para cada video, se elegirá una cara al azar de tu selección. "
                "**Asegúrate de que el servicio de FaceFusion esté corriendo en `http://127.0.0.1:5100`**."
            )
            
            # El CheckboxGroup se carga dinámicamente al iniciar el script
            modelos_disponibles = obtener_modelos_disponibles()
            checkbox_modelos = gr.CheckboxGroup(
                choices=modelos_disponibles, 
                label="Modelos de Cara a Utilizar", 
                # Selecciona el primero por defecto si existe, si no, deja la lista vacía
                value=modelos_disponibles[0] if modelos_disponibles else [],
                interactive=True
            )

            btn_face_swap = gr.Button("🎭 Realizar Face Swap Aleatorio", variant="primary")
            
            gr.Markdown("---")
            
            gr.Markdown("### Paso 5: Post-Procesar")
            gr.Markdown("Aplica transformaciones sutiles a los videos en `videos_finales` para crear variantes.")
            with gr.Row():
                crf_slider = gr.Slider(18, 28, value=21, step=1, label="CRF (Calidad, menor es mejor)")
                preset_dropdown = gr.Dropdown(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"], value="medium", label="Preset (Velocidad)")
                seed_input = gr.Textbox("123", label="Semilla (Seed) para aleatoriedad")
            
            btn_postprocesar = gr.Button("✨ Iniciar Post-Procesamiento", variant="primary")

        with gr.TabItem("4. Limpieza"):
            gr.Markdown("### Limpiar Carpetas de Videos")
            gr.Markdown("Selecciona las carpetas cuyo contenido deseas eliminar permanentemente. Esta acción no se puede deshacer.")
            with gr.Group():
                cb_originales = gr.Checkbox(True, label="Eliminar Videos Originales")
                cb_finales = gr.Checkbox(True, label="Eliminar Videos con FaceSwap")
                cb_procesados = gr.Checkbox(True, label="Eliminar Videos Post-Procesados")
                cb_anticopyright = gr.Checkbox(True, label="Eliminar Videos Anticopyright (en 'anticopryng')")
            
            btn_limpiar = gr.Button("🗑️ Limpiar Carpetas Seleccionadas", variant="stop")

        with gr.TabItem("5. Anticopyright"):
            gr.Markdown("### Paso Final: Aplicar Procesamiento Anti-Copyright")
            gr.Markdown(
                "Toma los videos de `swap/videos_finales_procesados` y les aplica transformaciones avanzadas. "
                "Los resultados se guardan en `anticopryng/videos_anticopyright`."
            )
            with gr.Row():
                ciclos_slider = gr.Slider(1, 10, value=1, step=1, label="Número de Ciclos de Procesamiento por Video")
            
            btn_anticopyright = gr.Button("🛡️ Iniciar Proceso Anti-Copyright", variant="primary")
        # --- PESTAÑA 6 MODIFICADA CON CONFIGURACIÓN INTEGRADA ---
        with gr.TabItem("6. Publicar en Facebook (Auto)"):
            gr.Markdown("### 🤖 Publicación Automática con IA")
            
            # Sección desplegable para la configuración, oculta por defecto
            with gr.Accordion("🔑 Configuración de Publicación (Facebook)", open=False):
                gr.Markdown("Introduce tus credenciales de la API de Facebook. Se guardarán en un archivo `config.ini` en la misma carpeta que este script.")
                
                # Cargamos los valores guardados al iniciar la app para que aparezcan en los campos
                initial_page_id, initial_token = cargar_configuracion_facebook()
                
                fb_page_id_textbox = gr.Textbox(value=initial_page_id, label="🆔 ID de la Página de Facebook")
                fb_token_textbox = gr.Textbox(value=initial_token, label="🔑 Token de Acceso de Facebook", type="password")
                btn_save_config = gr.Button("💾 Guardar Configuración de Facebook", variant="primary")

            gr.Markdown("---")
            prompt_ia_textbox = gr.Textbox(
                label="🧠 Instrucciones para la IA (Prompt Base)",
                lines=4,
                value="""Crea un título llamativo y una descripción viral para un video de entretenimiento en redes sociales.

            FORMATO REQUERIDO:
            Título: [título de máximo 60 caracteres]
            Descripción: [descripción de 100-150 caracteres con emojis] #hashtag1 #hashtag2 #hashtag3

            REQUISITOS:
            - Título directo y llamativo
            - Descripción que invite a la interacción
            - Usar emojis relevantes
            - Exactamente 3 hashtags populares
            - Tono casual y atractivo para engagement
            - Generar contenido inmediatamente sin preguntas

            Genera el contenido ahora:""",
            )
            
            gr.Markdown("### ✔️ Videos a Publicar")
            with gr.Row():
                videos_checkboxgroup = gr.CheckboxGroup(
                    choices=obtener_videos_finales(),
                    label="Selecciona los videos a publicar"
                )
                btn_refresh_videos = gr.Button("🔄 Refrescar Lista")
            
            btn_publicar_auto = gr.Button("🚀 Iniciar Publicación Automática", variant="primary")
    # --- Lógica de los botones ---
    btn_crear_carpetas.click(fn=crear_estructura_carpetas, outputs=output_console).then(fn=get_url_content, outputs=url_editor)
    btn_save_urls.click(fn=save_url_content, inputs=url_editor, outputs=output_console)
    btn_refresh_urls.click(fn=get_url_content, inputs=None, outputs=url_editor)
    btn_descargar.click(fn=descargar_desde_archivo_gradio, outputs=output_console)
    
    # --- LÍNEA MODIFICADA EN LA LÓGICA DE BOTONES ---
    # Ahora pasamos el valor del CheckboxGroup como entrada a la función de face swap.
    btn_face_swap.click(fn=realizar_face_swap_gradio, inputs=checkbox_modelos, outputs=output_console)
    
    btn_postprocesar.click(fn=postprocesar_variantes_gradio, inputs=[crf_slider, preset_dropdown, seed_input], outputs=output_console)
    btn_limpiar.click(fn=limpiar_carpetas_videos_gradio, inputs=[cb_originales, cb_finales, cb_procesados, cb_anticopyright], outputs=output_console)
    btn_anticopyright.click(fn=iniciar_anticopyright_gradio, inputs=[ciclos_slider], outputs=output_console)
    # --- LÓGICA FINAL PARA LOS BOTONES DE LA PESTAÑA 6 ---
    
    # Conecta el nuevo botón de GUARDAR a la función de guardar.
    btn_save_config.click(
        fn=guardar_configuracion_facebook,
        inputs=[fb_page_id_textbox, fb_token_textbox],
        outputs=output_console
    )
    
    # Conecta el botón de PUBLICAR. Ahora coge las credenciales de los campos de texto de esta misma pestaña.
    btn_publicar_auto.click(
        fn=iniciar_publicacion_automatica_gradio,
        inputs=[
            videos_checkboxgroup, 
            prompt_ia_textbox,
            fb_page_id_textbox, # <-- Toma el ID desde el campo de la Pestaña 6
            fb_token_textbox    # <-- Toma el Token desde el campo de la Pestaña 6
        ],
        outputs=output_console
    )

    # La lógica para refrescar la lista de videos no cambia.
    btn_refresh_videos.click(
        fn=lambda: gr.CheckboxGroup(choices=obtener_videos_finales()), 
        inputs=None, 
        outputs=videos_checkboxgroup
    )

if __name__ == "__main__":
    # La primera vez, crea la estructura de carpetas automáticamente si no existe
    if not os.path.exists(SWAP_DIR):
        print("Primera ejecución: creando estructura de carpetas inicial...")
        crear_estructura_carpetas()
        
    demo.launch(theme=gr.themes.Soft())