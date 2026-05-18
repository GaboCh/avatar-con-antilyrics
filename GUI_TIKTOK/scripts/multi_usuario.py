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

def proceso_multi_usuario(
    texto_usuarios, texto_canales,
    max_videos, n_por_usuario, num_ciclos,
    modo_prueba, titulo_base, descripcion,
    es_shorts, tags_base, tags_modo
):
    """
    Generador que yield mensajes de progreso para la GUI.
    Flujo: descarga → anticopyright → cola round-robin → subida multi-canal.
    """
    sys.path.insert(0, script_dir)
    import subidor_youtube
    import multi_canal_auth

    stop_event.clear()

    usuarios = parsear_lista(texto_usuarios)
    canales  = parsear_lista(texto_canales)

    if not usuarios:
        yield "❌ Ingresa al menos un usuario de TikTok."
        return
    if not canales:
        yield "❌ Ingresa al menos un canal de YouTube."
        return

    # Verificar canales autenticados
    no_auth = [c for c in canales if not multi_canal_auth.canal_autenticado(c)]
    if no_auth:
        yield "❌ Los siguientes canales no estan autenticados:"
        for c in no_auth:
            yield f"   — {c}"
        yield "   Ve a la Pestana 1 → Gestion de Canales y autentica cada uno."
        return

    yield f"🚀 MULTI-USUARIO INICIADO\nUsuarios : {usuarios}\nCanales  : {canales}\n{'='*60}"

    # ── PASO 1: Descarga ──────────────────────────────────────
    yield "\n📥 PASO 1/3 — Descargando videos por usuario..."
    cookies_ok = False
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, encoding='utf-8') as _f:
            cookies_ok = any(l.strip() and not l.startswith('#') for l in _f)
    if not cookies_ok:
        yield "⚠️  Cookies vacias. Configuralas en la Pestana 1 antes de continuar."
        return

    for u in usuarios:
        if stop_event.is_set():
            yield "⏹️ Proceso detenido por el usuario."
            return
        yield f"   📥 Descargando @{u} (max {int(max_videos)} videos)..."
        try:
            videos, stdout, code = descargar_usuario(u, max_videos)
            yield f"   ✅ @{u}: {len(videos)} videos en carpeta"
            if stdout:
                for linea in stdout.strip().splitlines()[-5:]:
                    yield f"      {linea}"
        except Exception as e:
            yield f"   ❌ @{u}: Error — {e}"

    # ── PASO 2: Anticopyright ─────────────────────────────────
    yield f"\n🛡️ PASO 2/3 — Anticopyright ({int(num_ciclos)} ciclos)..."
    if not os.path.exists(APP_VIDEO_SCRIPT):
        yield f"❌ No se encontro app_video.py en: {GUI_ANTICOPY_DIR}"
        return

    for u in usuarios:
        if stop_event.is_set():
            yield "Proceso detenido por el usuario."
            return
        yield f"   >> Procesando @{u} con anticopyright..."
        try:
            procesados = []
            for item in procesar_usuario(u, num_ciclos, es_shorts):
                if isinstance(item, list):
                    # Ultimo valor: lista de archivos procesados
                    procesados = item
                else:
                    # Linea de log en tiempo real
                    yield item
            yield f"   OK @{u}: {len(procesados)} videos procesados"
        except Exception as e:
            yield f"   ERR @{u}: {e}"

    # ── PASO 3: Cola round-robin ──────────────────────────────
    yield f"\n📋 PASO 3/3 — Construyendo cola round-robin ({int(n_por_usuario)} por usuario)..."
    cola = construir_cola_round_robin(usuarios, int(n_por_usuario))
    yield f"   Total videos a subir: {len(cola)}"

    if not cola:
        yield "❌ No hay videos procesados para subir. Verifica el paso anterior."
        return

    # ── PASO 4: Autenticar canales ────────────────────────────
    yield "\n🔑 Autenticando canales de YouTube..."
    youtube_por_canal = {}
    for canal in canales:
        yt = multi_canal_auth.obtener_youtube_canal(canal)
        if yt:
            youtube_por_canal[canal] = yt
            yield f"   ✅ Canal '{canal}' listo"
        else:
            yield f"   ❌ Canal '{canal}' fallo autenticacion — se omitira"

    if not youtube_por_canal:
        yield "❌ Ningun canal pudo autenticarse. Proceso detenido."
        return

    canales_activos = [c for c in canales if c in youtube_por_canal]
    extra_tags = [t.strip() for t in tags_base.split(',') if t.strip()]

    # ── PASO 5: Subida intercalada ────────────────────────────
    yield f"\n📤 Iniciando subida — {len(cola)} videos → {len(canales_activos)} canales...\n{'='*60}"

    for idx, (video_path, usuario_origen) in enumerate(cola):
        if stop_event.is_set():
            yield "⏹️ Scheduler detenido por el usuario."
            return

        canal   = canales_activos[idx % len(canales_activos)]
        youtube = youtube_por_canal[canal]
        nombre  = os.path.basename(video_path)

        titulo_tiktok = os.path.splitext(nombre)[0].split('__')[0].replace('_', ' ').strip()
        titulo = f"{titulo_base} {idx+1}" if titulo_base.strip() else titulo_tiktok or f"Video {idx+1}"
        desc   = descripcion or ''

        if es_shorts:
            if '#Shorts' not in titulo:
                titulo = f"{titulo} #Shorts"
            if '#Shorts' not in desc:
                desc = f"#Shorts #Short\n{desc}"

        yield (f"\n📤 [{idx+1}/{len(cola)}] @{usuario_origen} → Canal '{canal}'\n"
               f"   Archivo: {nombre}\n"
               f"   Titulo : {titulo}")

        try:
            tags = subidor_youtube.obtener_tags_trending(youtube, extra_tags=extra_tags)
            if tags_modo == '❌ Sin tags':
                tags = []
            elif tags_modo == '🎲 Aleatorio' and random.random() < 0.5:
                tags = []

            subidor_youtube.subir_video(youtube, video_path, titulo, desc, tags=tags)
            yield "   ✅ Subido correctamente"
        except Exception as e:
            yield f"   ❌ Error al subir: {e}"
            continue

        if idx < len(cola) - 1:
            espera = 4 * 60 if modo_prueba else random.randint(15, 30) * 60
            mins   = espera // 60
            yield f"   ⏳ Esperando {mins} min antes del siguiente..."
            time.sleep(espera)

    yield f"\n{'*'*60}\n✅ PROCESO MULTI-USUARIO COMPLETADO\n{'*'*60}"


def detener():
    """Senaliza al proceso para que se detenga despues del video actual."""
    stop_event.set()
