"""
multi_usuario.py
Descarga, procesa y sube videos de multiples usuarios TikTok
a multiples canales de YouTube en orden round-robin.
Modulo independiente — no importa tiktok_youtube_gui.py.
"""
import os
import sys
import glob
import shutil
import subprocess
import time
import random
import threading

script_dir      = os.path.abspath(os.path.dirname(__file__))
gui_tiktok_dir  = os.path.dirname(script_dir)

BASE_DIR          = os.path.join(gui_tiktok_dir, 'proyectos_tiktok')
COOKIES_FILE      = os.path.join(BASE_DIR, 'cookies', 'www.tiktok.com_cookies.txt')
VIDEOS_ORIGINALES = os.path.join(BASE_DIR, 'videos_originales')
VIDEOS_PROCESADOS = os.path.join(BASE_DIR, 'videos_procesados')
GUI_ANTICOPY_DIR  = os.path.join(gui_tiktok_dir, 'anticopryng')
APP_VIDEO_SCRIPT  = os.path.join(GUI_ANTICOPY_DIR, 'app_video.py')

# Stop event compartido para poder detener el proceso desde la GUI
stop_event = threading.Event()


# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────

def parsear_lista(texto):
    """Convierte texto (comas o saltos de linea) en lista de strings limpios."""
    return [
        item.strip().lstrip('@')
        for item in texto.replace(',', '\n').splitlines()
        if item.strip().lstrip('@')
    ]


# ─────────────────────────────────────────────
# PASO 1 — DESCARGA
# ─────────────────────────────────────────────

def descargar_usuario(username, max_videos):
    """
    Descarga hasta max_videos videos de @username a:
      videos_originales/{username}/
    Usa un archive file propio por usuario para no repetir descargas.
    Retorna (lista_de_mp4, stdout, returncode).
    """
    carpeta  = os.path.join(VIDEOS_ORIGINALES, username)
    archive  = os.path.join(BASE_DIR, f'descargados_{username}.txt')
    os.makedirs(carpeta, exist_ok=True)

    url = f'https://www.tiktok.com/@{username}'

    cmd = [
        sys.executable, '-m', 'yt_dlp', url,
        '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/mp4',
        '--merge-output-format', 'mp4',
        '--match-filter', '!is_live',
        '--ignore-errors',
        '--output', os.path.join(carpeta, '%(title).60s__%(id)s.%(ext)s'),
        '--restrict-filenames',
        '--no-warnings',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '--add-header', 'Referer:https://www.tiktok.com/',
        '--extractor-retries', '5',
        '--socket-timeout', '30',
        '--sleep-interval', '3',
        '--max-sleep-interval', '8',
        '--max-downloads', str(int(max_videos)),
        '--cookies', COOKIES_FILE,
        '--download-archive', archive,
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True,
        timeout=900, encoding='utf-8', errors='ignore'
    )
    videos = sorted(glob.glob(os.path.join(carpeta, '*.mp4')))
    return videos, result.stdout, result.returncode


# ─────────────────────────────────────────────
# PASO 2 — ANTICOPYRIGHT
# ─────────────────────────────────────────────

def procesar_usuario(username, num_ciclos, es_shorts):
    """
    Generador: aplica anticopyright a todos los .mp4 de videos_originales/{username}/
    y mueve los procesados a videos_procesados/{username}/.
    Hace yield de cada linea de log del proceso en tiempo real.
    Al terminar hace yield de la lista de rutas procesadas como ultimo valor.
    """
    carpeta_in  = os.path.join(VIDEOS_ORIGINALES, username)
    carpeta_out = os.path.join(VIDEOS_PROCESADOS, username)
    os.makedirs(carpeta_out, exist_ok=True)

    videos = sorted(glob.glob(os.path.join(carpeta_in, '*.mp4')))
    procesados = []

    for i, video_path in enumerate(videos):
        work  = os.path.join(gui_tiktok_dir, f'temp_multi_{username}_{i}')
        w_in  = os.path.join(work, 'videos_finales')
        w_out = os.path.join(work, 'videos_finales_procesados')

        try:
            if os.path.exists(work):
                shutil.rmtree(work)
            os.makedirs(w_in)
            os.makedirs(w_out)
            shutil.copy(video_path, w_in)

            yield f"      Video {i+1}/{len(videos)}: {os.path.basename(video_path)}"

            cmd = [
                sys.executable, '-u', APP_VIDEO_SCRIPT,
                w_in, w_out,
                str(int(num_ciclos)),
                '1' if es_shorts else '0',
            ]
            proceso = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            for linea_raw in proceso.stdout:
                linea_raw = linea_raw.rstrip()
                if linea_raw:
                    yield f"      | {linea_raw}"
            proceso.wait()

            archivos = glob.glob(os.path.join(w_in, '*.mp4'))
            if archivos:
                destino = os.path.join(carpeta_out, os.path.basename(archivos[0]))
                shutil.move(archivos[0], destino)
                procesados.append(destino)
                yield f"      OK guardado: {os.path.basename(destino)}"
            else:
                yield f"      WARN: no se genero video de salida para {os.path.basename(video_path)}"

        except Exception as e:
            yield f"      ERR: {e}"
        finally:
            if os.path.exists(work):
                shutil.rmtree(work)

    # Ultimo yield: devuelve la lista de procesados para que el orquestador la use
    yield procesados


# ─────────────────────────────────────────────
# PASO 3 — COLA ROUND-ROBIN
# ─────────────────────────────────────────────

def construir_cola_round_robin(usuarios, n_por_usuario):
    """
    Construye una lista intercalada de (video_path, username).
    Ejemplo con n=2 y 2 usuarios:
      [u1_v1, u1_v2, u2_v1, u2_v2, u1_v3, u1_v4, ...]
    """
    listas = {}
    for u in usuarios:
        carpeta = os.path.join(VIDEOS_PROCESADOS, u)
        videos  = sorted(glob.glob(os.path.join(carpeta, '*.mp4')))
        if videos:
            listas[u] = videos

    cola    = []
    indices = {u: 0 for u in listas}
    activos = [u for u in usuarios if u in listas]

    while activos:
        for u in list(activos):
            idx   = indices[u]
            chunk = listas[u][idx: idx + n_por_usuario]
            for v in chunk:
                cola.append((v, u))
            indices[u] += n_por_usuario
            if indices[u] >= len(listas[u]):
                activos.remove(u)

    return cola


# ─────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# ─────────────────────────────────────────────

import queue
import threading
from concurrent.futures import ThreadPoolExecutor

def proceso_multi_usuario(
    texto_usuarios, texto_canales,
    max_videos, n_por_usuario, num_ciclos,
    modo_prueba, titulo_base, descripcion,
    es_shorts, tags_base, tags_modo, usar_base, usar_app_video
):
    """
    Pipeline Asíncrono Multi-Usuario:
    Hilo 1: Descarga videos secuencialmente.
    Hilo 2: Anticopyright (Obligatorio 65/35 -> Opcional app_video) en cuanto llegan.
    Hilo 3: Subida Round-Robin a múltiples canales en cuanto están procesados.
    """
    sys.path.insert(0, script_dir)
    import subidor_youtube
    import multi_canal_auth

    stop_event.clear()

    usuarios = parsear_lista(texto_usuarios)
    canales  = parsear_lista(texto_canales)

    if not usuarios or not canales:
        yield "❌ Ingresa al menos un usuario y un canal."
        return

    # Autenticar canales
    youtube_por_canal = {}
    for canal in canales:
        yt = multi_canal_auth.obtener_youtube_canal(canal)
        if yt:
            youtube_por_canal[canal] = yt
            
    canales_activos = [c for c in canales if c in youtube_por_canal]
    if not canales_activos:
        yield "❌ Ningún canal pudo autenticarse. Proceso detenido."
        return

    # Colas y señales
    log_queue   = queue.Queue()
    upload_queue = queue.Queue()   # Cola GLOBAL de videos listos para subir
    descarga_terminada     = threading.Event()
    anticopyright_terminado = threading.Event()

    def log(msg):
        log_queue.put(msg)

    yield f"🚀 MULTI-USUARIO INICIADO (FÁBRICA ASÍNCRONA)\nUsuarios : {usuarios}\nCanales  : {canales_activos}\n{'='*60}"

    # -------------------------------------------------------------
    # HILO 1: DESCARGA
    # -------------------------------------------------------------
    def hilo_descarga():
        for u in usuarios:
            if stop_event.is_set(): break
            log(f"📥 Descargando @{u}...")
            try:
                descargar_usuario(u, max_videos)
                log(f"✅ Descarga de @{u} completada.")
            except Exception as e:
                log(f"❌ Error descargando @{u}: {e}")
        descarga_terminada.set()
        log("🏁 Fase de descargas terminada.")

    # -------------------------------------------------------------
    # HILO 2: ANTICOPYRIGHT
    # -------------------------------------------------------------
    def procesar_un_video(video_path, u):
        idx = random.randint(1000, 9999)
        work = os.path.join(gui_tiktok_dir, f'temp_multi_{u}_{idx}')
        w_in = os.path.join(work, 'in')
        w_out1 = os.path.join(work, 'out1')
        w_out2 = os.path.join(work, 'out2')
        
        try:
            os.makedirs(w_in, exist_ok=True)
            os.makedirs(w_out1, exist_ok=True)
            os.makedirs(w_out2, exist_ok=True)
            shutil.copy(video_path, w_in)
            
            video_listo = video_path
            current_in = w_in
            
            # 1. Filtro Base (65/35 achatado + plasma)
            if usar_base:
                log(f"   ⚙️ Entrando en base 35 65 (ai_studio_code_agresivo) para {os.path.basename(video_path)}...")
                script_base = os.path.join(GUI_ANTICOPY_DIR, 'ai_studio_code_agresivo.py')
                p1 = subprocess.run([sys.executable, "-u", script_base, current_in, w_out1], capture_output=True, text=True, errors='ignore')
                for linea in p1.stdout.splitlines():
                    if linea.strip(): log(f"      [65/35] {linea.strip()}")
                
                archivos_out1 = glob.glob(os.path.join(w_out1, '*.mp4'))
                if not archivos_out1: return None
                video_listo = archivos_out1[0]
                current_in = w_out1
            
            # 2. Filtro Sutil (app_video.py) - OPCIONAL
            if usar_app_video:
                log(f"   ⚙️ Entrando a app_video.py (ciclos) para {os.path.basename(video_path)}...")
                p2 = subprocess.run([sys.executable, "-u", APP_VIDEO_SCRIPT, current_in, w_out2, str(int(num_ciclos)), "1" if es_shorts else "0"], capture_output=True, text=True, errors='ignore')
                for linea in p2.stdout.splitlines():
                    if linea.strip(): log(f"      [app_video] {linea.strip()}")
                
                archivos_out2 = glob.glob(os.path.join(w_out2, '*.mp4'))
                if archivos_out2: video_listo = archivos_out2[0]
            
            if not usar_base and not usar_app_video:
                # Si apagó todo, igual lo movemos a procesados para que se suba
                video_listo = os.path.join(w_out1, os.path.basename(video_path))
                shutil.copy(video_path, video_listo)
            
            carpeta_out_final = os.path.join(VIDEOS_PROCESADOS, u)
            os.makedirs(carpeta_out_final, exist_ok=True)
            destino_final = os.path.join(carpeta_out_final, os.path.basename(video_listo))
            shutil.move(video_listo, destino_final)
            return destino_final
        except Exception:
            return None
        finally:
            if os.path.exists(work): shutil.rmtree(work)

    # HILO 2: ANTICOPYRIGHT (versión con cola global)
    def hilo_anticopyright_seguro():
        en_proceso = set()
        procesados = set()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = {}  # futuro -> (original_path, usuario)
            
            while not stop_event.is_set():
                # Buscar archivos nuevos en todas las carpetas de usuarios
                for u in usuarios:
                    carpeta_in = os.path.join(VIDEOS_ORIGINALES, u)
                    if os.path.exists(carpeta_in):
                        actuales = set(glob.glob(os.path.join(carpeta_in, '*.mp4')))
                        nuevos = actuales - en_proceso - procesados
                        for vid in nuevos:
                            en_proceso.add(vid)
                            f = executor.submit(procesar_un_video, vid, u)
                            futuros[f] = (vid, u)
                
                # Chequear futuros completados
                terminados = [f for f in list(futuros) if f.done()]
                for f in terminados:
                    orig_path, u = futuros.pop(f)
                    dest_path = f.result()
                    en_proceso.discard(orig_path)
                    procesados.add(orig_path)
                    
                    if dest_path:
                        log(f"   🛡️ Listo para subir: {os.path.basename(dest_path)}")
                        upload_queue.put(dest_path)   # ← Cola GLOBAL
                    else:
                        log(f"   ❌ Error procesando: {os.path.basename(orig_path)}")
                
                if descarga_terminada.is_set() and len(futuros) == 0:
                    break
                time.sleep(1.0)
        
        # Señal de fin: un solo sentinel DONE
        upload_queue.put("DONE")
        anticopyright_terminado.set()
        log("🏁 Fase Anticopyright terminada. Cola de subida cerrada.")

    # HILO 3: UPLOADER (cola global, round-robin de canales)
    def hilo_upload():
        idx_canal   = 0
        extra_tags  = [t.strip() for t in tags_base.split(',') if t.strip()]
        
        while not stop_event.is_set():
            try:
                video_path = upload_queue.get(timeout=3)   # espera hasta 3 seg el próximo video
            except queue.Empty:
                # Si anticopyright ya terminó y la cola sigue vacía, salimos
                if anticopyright_terminado.is_set():
                    break
                continue   # si no, seguimos esperando
            
            if video_path == "DONE":
                break
            
            # Elegir canal en round-robin
            canal   = canales_activos[idx_canal % len(canales_activos)]
            idx_canal += 1
            youtube = youtube_por_canal[canal]
            
            nombre        = os.path.basename(video_path)
            titulo_tiktok = os.path.splitext(nombre)[0].split('__')[0].replace('_', ' ').strip()
            titulo = titulo_base.strip() if titulo_base.strip() else titulo_tiktok or "Video"
            desc   = descripcion or ''
            
            if es_shorts:
                if '#Shorts' not in titulo: titulo += " #Shorts"
                if '#Shorts' not in desc:   desc    = f"#Shorts #Short\n{desc}"
            
            log(f"\n📤 Subiendo a '{canal}': {nombre}")
            try:
                tags = subidor_youtube.obtener_tags_trending(youtube, extra_tags=extra_tags)
                if tags_modo == '❌ Sin tags':                                 tags = []
                elif tags_modo == '🎲 Aleatorio' and random.random() < 0.5: tags = []
                
                subidor_youtube.subir_video(youtube, video_path, titulo, desc, tags=tags)
                log("   ✅ Subido exitosamente")
            except Exception as e:
                log(f"   ❌ Error subiendo: {e}")
            
            # Esperar entre subidas (anti-spam YouTube)
            # Mientras dormimos, los otros 2 hilos siguen descargando y procesando
            if not anticopyright_terminado.is_set() or not upload_queue.empty():
                espera = 4 * 60 if modo_prueba else random.randint(15, 30) * 60
                log(f"   ⏳ Esperando {espera//60} min antes del siguiente (descarga y anticopyright siguen corriendo)...")
                tiempo_inicio = time.time()
                while time.time() - tiempo_inicio < espera:
                    if stop_event.is_set(): return
                    time.sleep(5)   # revisa cada 5 seg si se pidó detener
        
        log("🏁 Todos los uploads terminados.")

    # Arrancar hilos
    t_descarga = threading.Thread(target=hilo_descarga)
    t_anticopy = threading.Thread(target=hilo_anticopyright_seguro)
    t_upload   = threading.Thread(target=hilo_upload)
    
    t_descarga.start()
    t_anticopy.start()
    t_upload.start()

    historial_log = []
    while t_descarga.is_alive() or t_anticopy.is_alive() or t_upload.is_alive() or not log_queue.empty():
        while not log_queue.empty():
            historial_log.append(log_queue.get())
        if historial_log:
            yield "\n".join(historial_log[-40:])
        time.sleep(0.5)

    yield "\n".join(historial_log[-40:]) + "\n\n🎉 PROCESO MULTI-USUARIO ASÍNCRONO COMPLETADO."

def detener():
    stop_event.set()
