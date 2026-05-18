import os
import sys
import glob
import subprocess
import time
import random
import shutil
import threading
for _ in range(5):
    try:
        import gradio as gr
        break
    except KeyboardInterrupt:
        pass
else:
    raise RuntimeError("No se pudo cargar gradio")
from concurrent.futures import ThreadPoolExecutor, as_completed

# Modulos multi-usuario (se importan aqui para que los errores sean visibles al arrancar)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import multi_canal_auth
import multi_usuario

# --- RUTAS BASE ---
script_dir    = os.path.abspath(os.path.dirname(__file__))   # GUI_TIKTOK/scripts/
gui_tiktok_dir = os.path.dirname(script_dir)                 # GUI_TIKTOK/
avatar_dir    = os.path.dirname(gui_tiktok_dir)              # avatar/

BASE_DIR          = os.path.join(gui_tiktok_dir, 'proyectos_tiktok')
COOKIES_FILE      = os.path.join(BASE_DIR, 'cookies', 'www.tiktok.com_cookies.txt')
VIDEOS_ORIGINALES = os.path.join(BASE_DIR, 'videos_originales')
VIDEOS_PROCESADOS = os.path.join(BASE_DIR, 'videos_procesados')
CREDENCIALES_DIR  = os.path.join(BASE_DIR, 'credenciales_youtube')
ARCHIVE_FILE      = os.path.join(BASE_DIR, 'descargados.txt')
LOG_FILE          = os.path.join(BASE_DIR, 'actividad.log')

# Scripts anticopyright propios de GUI_TIKTOK
GUI_ANTICOPY_DIR  = os.path.join(gui_tiktok_dir, 'anticopryng')
APP_VIDEO_SCRIPT  = os.path.join(GUI_ANTICOPY_DIR, 'app_video.py')

# Carpetas temporales de trabajo para el anticopyright
WORK_DIR          = os.path.join(gui_tiktok_dir, 'temp_anticopy')
WORK_INPUT        = os.path.join(WORK_DIR, 'videos_finales')
WORK_OUTPUT       = os.path.join(WORK_DIR, 'videos_finales_procesados')


# --- CONSOLA VIRTUAL ---
class GradioConsole:
    def __init__(self):
        self.buffer = ""
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

    def write(self, text):
        self.buffer += text
        self.old_stdout.write(text)
        self.old_stdout.flush()
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as _lf:
                _lf.write(text)
        except Exception:
            pass

    def flush(self):
        pass

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

# --- ESTADO DEL SCHEDULER ---
scheduler_stop_event = threading.Event()
scheduler_log        = []
scheduler_lock       = threading.Lock()


# =========================================================
# PESTAÑA 1 - CONFIGURACIÓN
# =========================================================

def crear_estructura_carpetas():
    console.clear_buffer()
    console.start_redirect()

    print("📂 Creando estructura de carpetas...")

    carpetas = [
        os.path.join(BASE_DIR, 'cookies'),
        VIDEOS_ORIGINALES,
        VIDEOS_PROCESADOS,
        CREDENCIALES_DIR,
    ]
    for carpeta in carpetas:
        os.makedirs(carpeta, exist_ok=True)
        print(f"🟢 {os.path.relpath(carpeta, avatar_dir)}")

    # Archivo de cookies TikTok
    if not os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write('# Netscape HTTP Cookie File\n# Pega aqui tus cookies de TikTok debajo de esta linea\n')
        print(f"🍪 Creado: {COOKIES_FILE}")

    # Plantilla client_secrets.json
    client_secrets = os.path.join(CREDENCIALES_DIR, 'client_secrets.json')
    if not os.path.exists(client_secrets):
        with open(client_secrets, 'w', encoding='utf-8') as f:
            f.write('{\n'
                    '  "installed": {\n'
                    '    "client_id": "PEGA_TU_CLIENT_ID_AQUI",\n'
                    '    "client_secret": "PEGA_TU_CLIENT_SECRET_AQUI",\n'
                    '    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],\n'
                    '    "auth_uri": "https://accounts.google.com/o/oauth2/auth",\n'
                    '    "token_uri": "https://accounts.google.com/o/oauth2/token"\n'
                    '  }\n'
                    '}\n')
        print(f"🔑 Plantilla creada: {client_secrets}")
        print("   ⚠️  Edita ese archivo con tus credenciales de Google Cloud Console.")

    print("\n✅ Estructura lista.")
    output = console.get_buffer()
    console.stop_redirect()
    return output


def get_cookies_content():
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    return "# Crea la estructura primero (Paso 1)"


def save_cookies_content(content):
    try:
        os.makedirs(os.path.dirname(COOKIES_FILE), exist_ok=True)
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        return "✅ Cookies de TikTok guardadas."
    except Exception as e:
        return f"❌ Error al guardar: {e}"


# =========================================================
# PESTAÑA 2 - DESCARGAR FAVORITOS TIKTOK
# =========================================================

def descargar_favoritos_tiktok(username, max_videos):
    console.clear_buffer()
    console.start_redirect()

    if not username.strip():
        print("❌ Ingresa tu nombre de usuario de TikTok.")
        output = console.get_buffer()
        console.stop_redirect()
        return output

    username  = username.strip().lstrip('@')
    max_videos = int(max_videos)

    # Verificar cookies
    cookies_ok = False
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, encoding='utf-8') as _f:
            cookies_ok = any(l.strip() and not l.startswith('#') for l in _f)
    if not cookies_ok:
        print("⚠️  Cookies vacías o no configuradas. Ve a la Pestaña 1.")
        output = console.get_buffer()
        console.stop_redirect()
        return output

    url = f"https://www.tiktok.com/@{username}"
    print(f"👤 Descargando videos del perfil de @{username}...")
    print(f"🔗 URL: {url}")
    print(f"📊 Máximo: {max_videos} videos")
    print("-" * 60)

    cmd = [
        sys.executable, '-m', 'yt_dlp', url,
        '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/mp4',
        '--merge-output-format', 'mp4',
        '--match-filter', '!is_live',
        '--ignore-errors',
        '--output', os.path.join(VIDEOS_ORIGINALES, '%(title).60s__%(id)s.%(ext)s'),
        '--restrict-filenames',
        '--no-warnings',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '--add-header', 'Referer:https://www.tiktok.com/',
        '--extractor-retries', '5',
        '--socket-timeout', '30',
        '--sleep-interval', '3',
        '--max-sleep-interval', '8',
        '--max-downloads', str(max_videos),
        '--cookies', COOKIES_FILE,
        '--download-archive', ARCHIVE_FILE,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=900, encoding='utf-8', errors='ignore')
        if result.stdout:
            print(result.stdout)
        if result.returncode in (0, 101):
            videos = glob.glob(os.path.join(VIDEOS_ORIGINALES, '*.mp4'))
            print(f"\n✅ Descarga completada. Videos en carpeta: {len(videos)}")
        else:
            print(f"❌ Error (código {result.returncode}):")
            print(result.stderr)
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout. Intenta con menos videos.")
    except Exception as e:
        print(f"❌ Error: {e}")

    output = console.get_buffer()
    console.stop_redirect()
    return output


# =========================================================
# PESTAÑA 3 - ANTICOPYRIGHT
# =========================================================

def iniciar_anticopyright(num_ciclos, es_shorts=False):
    """
    Generador: hace yield del log acumulado despues de cada linea del subproceso.
    Gradio 4 muestra el resultado en tiempo real cuando la funcion es un generador.
    """
    lineas = []

    def log(msg):
        lineas.append(msg)

    def pantalla():
        return "\n".join(lineas)

    if not os.path.exists(APP_VIDEO_SCRIPT):
        yield f"❌ No se encontró app_video.py en: {GUI_ANTICOPY_DIR}\n   Asegúrate de que la carpeta anticopryng/ existe."
        return

    videos = sorted(glob.glob(os.path.join(VIDEOS_ORIGINALES, '*.mp4')))
    if not videos:
        yield f"⚠️ No hay videos en {VIDEOS_ORIGINALES}\n   Descarga videos primero en la Pestaña 2."
        return

    log(f"🛡️ Anticopyright: {len(videos)} videos × {int(num_ciclos)} ciclos")
    log(f"   Scripts en: {GUI_ANTICOPY_DIR}")
    log("=" * 60)
    yield pantalla()

    os.makedirs(VIDEOS_PROCESADOS, exist_ok=True)

    for idx, video_path in enumerate(videos):
        nombre = os.path.basename(video_path)
        log(f"\n🔄 [{idx+1}/{len(videos)}] Procesando: {nombre}")
        yield pantalla()

        work  = os.path.join(gui_tiktok_dir, f'temp_anticopy_{idx}')
        w_in  = os.path.join(work, 'videos_finales')
        w_out = os.path.join(work, 'videos_finales_procesados')

        try:
            if os.path.exists(work):
                shutil.rmtree(work)
            os.makedirs(w_in)
            os.makedirs(w_out)
            shutil.copy(video_path, w_in)

            cmd = [
                sys.executable, "-u",   # -u = stdout sin buffer
                APP_VIDEO_SCRIPT,
                w_in,
                w_out,
                str(int(num_ciclos)),
                "1" if es_shorts else "0"
            ]
            log(f"   CMD: {' '.join(cmd)}")
            yield pantalla()

            # Leer salida linea por linea en tiempo real
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
                    log(f"   | {linea_raw}")
                    yield pantalla()
            proceso.wait()

            if proceso.returncode != 0:
                log(f"   ❌ Proceso terminó con código: {proceso.returncode}")
                yield pantalla()
            else:
                archivos = glob.glob(os.path.join(w_in, '*.mp4'))
                if archivos:
                    nombre_final = os.path.basename(archivos[0])
                    shutil.move(archivos[0], os.path.join(VIDEOS_PROCESADOS, nombre_final))
                    log(f"   ✅ Guardado en procesados: {nombre_final}")
                else:
                    log(f"   ❌ No se encontró video de salida en {w_in}")
                yield pantalla()

        except Exception as e:
            log(f"   ❌ Error inesperado: {e}")
            yield pantalla()
        finally:
            if os.path.exists(work):
                shutil.rmtree(work)

    log(f"\n{'*'*60}")
    log(f"✅ Anticopyright completado.")
    log(f"   Videos listos en: {VIDEOS_PROCESADOS}")
    log(f"{'*'*60}")
    yield pantalla()



# =========================================================
# PROCESO COMPLETO
# =========================================================

def proceso_completo(username, max_videos, num_ciclos, modo_prueba, titulo_base, descripcion_base, es_shorts, pc_vertical=False, tags_base='', tags_modo='🎲 Aleatorio'):
    yield "🚀 INICIANDO PROCESO COMPLETO\n" + "=" * 60

    # PASO 1: Descargar
    yield "📥 PASO 1/3 - Descargando videos..."
    result = descargar_favoritos_tiktok(username, max_videos)
    yield result

    videos = glob.glob(os.path.join(VIDEOS_ORIGINALES, '*.mp4'))
    if not videos:
        yield "❌ No se descargaron videos. Proceso detenido."
        return

    # PASO 2: Anticopyright
    yield "🛡️ PASO 2/3 - Aplicando anticopyright..."
    result = iniciar_anticopyright(num_ciclos, pc_vertical)
    yield result

    procesados = glob.glob(os.path.join(VIDEOS_PROCESADOS, '*.mp4'))
    if not procesados:
        yield "❌ No se procesaron videos. Proceso detenido."
        return

    # PASO 3: Subir a YouTube
    yield "📤 PASO 3/3 - Iniciando scheduler de YouTube..."
    for msg in iniciar_scheduler_youtube(modo_prueba, titulo_base, descripcion_base, es_shorts, tags_base, tags_modo):
        yield msg


# =========================================================
# PESTAÑA 4 - YOUTUBE
# =========================================================

def autenticar_youtube_gui():
    console.clear_buffer()
    console.start_redirect()
    try:
        sys.path.insert(0, script_dir)
        import subidor_youtube
        youtube = subidor_youtube.autenticar_youtube(CREDENCIALES_DIR)
        if youtube:
            print("✅ Autenticación con YouTube exitosa.")
            print("   Token guardado en credenciales_youtube/token.pickle")
        else:
            print("❌ No se pudo autenticar.")
    except ImportError as e:
        print(f"❌ Falta instalar paquetes: {e}")
        print("   Ejecuta: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    except Exception as e:
        print(f"❌ Error: {e}")
    output = console.get_buffer()
    console.stop_redirect()
    return output


def cambiar_canal_youtube():
    token_path = os.path.join(CREDENCIALES_DIR, 'token.pickle')
    if os.path.exists(token_path):
        try:
            os.remove(token_path)
            return "✅ Sesión cerrada. Haz clic en 'Autenticar con YouTube' para iniciar sesión con otro canal."
        except Exception as e:
            return f"❌ No se pudo eliminar el token: {e}"
    return "ℹ️ No hay sesión activa. Usa 'Autenticar con YouTube' para iniciar sesión."


def obtener_videos_procesados():
    videos = sorted(glob.glob(os.path.join(VIDEOS_PROCESADOS, '*.mp4')))
    if videos:
        return [os.path.basename(v) for v in videos]
    return ["No hay videos procesados aún..."]


def iniciar_scheduler_youtube(modo_prueba, titulo_base, descripcion_base, es_shorts, tags_base='', tags_modo='🎲 Aleatorio'):
    global scheduler_log

    scheduler_stop_event.clear()
    with scheduler_lock:
        scheduler_log = []

    videos = sorted(glob.glob(os.path.join(VIDEOS_PROCESADOS, '*.mp4')))
    if not videos:
        yield "❌ No hay videos procesados. Ejecuta el Anticopyright primero."
        return

    modo_txt = "🧪 PRUEBA (4 min)" if modo_prueba else "📅 NORMAL (15-30 min aleatorio)"
    lineas = []

    def log(msg):
        with scheduler_lock:
            scheduler_log.append(msg)
        lineas.append(msg)

    def actualizar_ultima(msg):
        with scheduler_lock:
            if scheduler_log and scheduler_log[-1].startswith("⏳"):
                scheduler_log[-1] = msg
        if lineas and lineas[-1].startswith("⏳"):
            lineas[-1] = msg

    def pantalla():
        return "\n".join(lineas)

    try:
        sys.path.insert(0, script_dir)
        import subidor_youtube
        youtube = subidor_youtube.autenticar_youtube(CREDENCIALES_DIR)
        if not youtube:
            yield "❌ No se pudo autenticar con YouTube."
            return

        log(f"🚀 Scheduler iniciado — Modo: {modo_txt}")
        log(f"📹 Videos a subir: {len(videos)}")
        log("🏷️ Obteniendo tags trending...")
        yield pantalla()

        extra = [t.strip() for t in tags_base.split(',') if t.strip()]
        tags  = subidor_youtube.obtener_tags_trending(youtube, extra_tags=extra)
        log(f"   Tags: {tags}")
        log("=" * 60)
        yield pantalla()

        for idx, video_path in enumerate(videos):
            if scheduler_stop_event.is_set():
                log("⏹️ Scheduler detenido por el usuario.")
                yield pantalla()
                return

            nombre = os.path.basename(video_path)
            titulo_tiktok = os.path.splitext(nombre)[0].split('__')[0].replace('_', ' ').strip()
            titulo = f"{titulo_base} {idx + 1}" if titulo_base.strip() else titulo_tiktok or f"Video {idx + 1}"
            desc   = descripcion_base or ''
            if es_shorts:
                if '#Shorts' not in titulo:
                    titulo = f"{titulo} #Shorts"
                if '#Shorts' not in desc:
                    desc = f"#Shorts #Short\n{desc}"

            log(f"\n📤 [{idx+1}/{len(videos)}] Subiendo: {nombre}")
            log(f"   Título: {titulo}")
            yield pantalla()

            # Subida en hilo separado con progreso en tiempo real
            _resultado = [None]
            _error     = [None]
            _nuevo     = threading.Event()

            def _progress(msg):
                # Actualiza la última línea de progreso en lugar de acumular
                with scheduler_lock:
                    if scheduler_log and scheduler_log[-1].startswith("   📤"):
                        scheduler_log[-1] = msg
                if lineas and lineas[-1].startswith("   📤"):
                    lineas[-1] = msg
                else:
                    log(msg)
                _nuevo.set()

            if tags_modo == '✅ Siempre con tags':
                usar_tags = True
            elif tags_modo == '❌ Sin tags':
                usar_tags = False
            else:
                usar_tags = random.choice([True, False])
            tags_video = tags if usar_tags else []
            log(f"   🏷️ Tags: {'sí' if tags_video else 'sin tags (aleatorio)'}")

            def _upload():
                try:
                    _resultado[0] = subidor_youtube.subir_video(
                        youtube, video_path, titulo, desc, tags=tags_video, progress_fn=_progress)
                except Exception as e:
                    _error[0] = e
                _nuevo.set()

            t_up = threading.Thread(target=_upload, daemon=True)
            t_up.start()
            while t_up.is_alive():
                _nuevo.wait(timeout=2)
                _nuevo.clear()
                yield pantalla()
            t_up.join()

            if _error[0]:
                log(f"   ❌ Error subiendo {nombre}: {_error[0]}")
            else:
                log(f"   ✅ Subido: https://youtu.be/{_resultado[0]['id']}")
            yield pantalla()

            if idx < len(videos) - 1 and not scheduler_stop_event.is_set():
                espera = 4 * 60 if modo_prueba else random.randint(15, 30) * 60
                minutos_total = espera // 60
                log(f"⏳ Próximo video en {minutos_total} min")
                yield pantalla()

                restante = espera
                while restante > 0 and not scheduler_stop_event.is_set():
                    tick = min(60, restante)
                    scheduler_stop_event.wait(timeout=tick)
                    restante -= tick
                    if restante > 0 and not scheduler_stop_event.is_set():
                        m = (restante + 59) // 60
                        actualizar_ultima(f"⏳ Próximo video en {m} min")
                        yield pantalla()

        log("\n🎯 Scheduler completado.")
        yield pantalla()

    except Exception as e:
        log(f"❌ Error fatal en scheduler: {e}")
        yield pantalla()


def ver_log_scheduler():
    with scheduler_lock:
        return "\n".join(scheduler_log[-150:]) if scheduler_log else "Sin actividad aún."


def detener_scheduler():
    scheduler_stop_event.set()
    return "⏹️ Señal de stop enviada. El upload en curso terminará antes de parar."


# =========================================================
# PESTAÑA 5 - LIMPIEZA
# =========================================================

def limpiar_carpetas(limpiar_originales, limpiar_procesados, limpiar_temp=True):
    console.clear_buffer()
    console.start_redirect()

    print("🗑️ Iniciando limpieza...")

    if limpiar_temp:
        import glob as _glob
        temps = _glob.glob(os.path.join(gui_tiktok_dir, 'temp_anticopy_*'))
        for t in temps:
            try:
                shutil.rmtree(t)
                print(f"🧹 Eliminado: {os.path.basename(t)}")
            except Exception as e:
                print(f"❌ No se pudo eliminar {os.path.basename(t)}: {e}")

    carpetas = {}
    if limpiar_originales:
        carpetas["Videos Originales (TikTok)"] = VIDEOS_ORIGINALES
    if limpiar_procesados:
        carpetas["Videos Procesados (anticopyright)"] = VIDEOS_PROCESADOS

    for nombre, ruta in carpetas.items():
        archivos = glob.glob(os.path.join(ruta, '*'))
        count = 0
        for f in archivos:
            try:
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.remove(f)
                count += 1
            except Exception as e:
                print(f"❌ No se pudo eliminar {os.path.basename(f)}: {e}")
        print(f"🧹 {nombre}: {count} archivos eliminados.")

    print("✅ Limpieza completada.")
    output = console.get_buffer()
    console.stop_redirect()
    return output


# =========================================================
# HELPERS PESTAÑA 8 — MULTI-USUARIO
# =========================================================

_MU_MAX_CANALES = 8   # numero maximo de slots de canal en la UI


def _mu_get_estado(nombre):
    try:
        nombre = (nombre or "").strip()
        if not nombre:
            return "⚠️ Sin nombre"
        if multi_canal_auth.canal_autenticado(nombre):
            nombre_real = multi_canal_auth.leer_nombre_real(nombre)
            display     = nombre_real if nombre_real else nombre
            return f"✅ {display}"
        return f"{nombre} — ⚠️ Sin token"
    except Exception as e:
        return f"❌ Error: {e}"

def _mu_refrescar_estados(*nombres):
    """Actualiza el estado visible de todos los slots usando los nombres actuales."""
    return [_mu_get_estado(n) for n in nombres]

def _mu_autenticar_y_estado(nombre):
    """Autentica el canal con ese nombre y retorna (mensaje_consola, nuevo_estado)."""
    nombre = (nombre or "").strip()
    if not nombre:
        return "❌ Escribe un nombre para el canal primero.", "⚠️ Sin nombre"
    msg = multi_canal_auth.autenticar_canal(nombre)
    return msg, _mu_get_estado(nombre)

def _mu_borrar_y_estado(nombre):
    """Borra token del canal con ese nombre y retorna (mensaje_consola, nuevo_estado)."""
    nombre = (nombre or "").strip()
    if not nombre:
        return "❌ Escribe un nombre para el canal primero.", "⚠️ Sin nombre"
    msg = multi_canal_auth.eliminar_canal(nombre)
    return msg, _mu_get_estado(nombre)

def _mu_iniciar(texto_usuarios, *rest):
    """
    Wrapper que recoge nombres y checks del UI y llama proceso_multi_usuario.
    rest = [name0..name7, ch0..ch7, max, rr, ciclos, prueba, titulo, desc, shorts, tags, tags_modo]
    """
    n      = _MU_MAX_CANALES
    names  = rest[:_MU_MAX_CANALES]
    checks = rest[_MU_MAX_CANALES:_MU_MAX_CANALES * 2]
    params = rest[_MU_MAX_CANALES * 2:]

    canales_activos = [names[i].strip() for i in range(n) if checks[i] and (names[i] or "").strip()]
    if not canales_activos:
        yield "❌ Marca al menos un canal con el checkbox 'Usar' y asegurate de que tenga nombre."
        return

    texto_canales                                                    = '\n'.join(canales_activos)
    max_v, rr, ciclos, prueba, titulo, desc, shorts, tags, tags_modo = params

    yield from multi_usuario.proceso_multi_usuario(
        texto_usuarios, texto_canales,
        max_v, rr, ciclos,
        prueba, titulo, desc, shorts, tags, tags_modo
    )


# =========================================================
# INTERFAZ GRADIO
# =========================================================

with gr.Blocks() as demo:
    gr.Markdown("# 🎵 TikTok Favoritos → Anticopyright → YouTube Auto-Uploader")

    output_console = gr.Textbox(
        label="📄 Consola de Salida", lines=15,
        interactive=False
    )

    with gr.Tabs():

        # --- PESTAÑA 1 ---
        with gr.TabItem("1. Configuración"):
            gr.Markdown("### Paso 1: Crear carpetas y configurar cookies de TikTok")
            btn_crear = gr.Button("📁 Crear Estructura de Carpetas", variant="secondary")

            gr.Markdown("### Cookies de TikTok")
            gr.Markdown(
                "1. Inicia sesión en TikTok en tu navegador.\n"
                "2. Instala la extensión **Get cookies.txt LOCALLY** (Chrome/Firefox).\n"
                "3. Exporta las cookies de `tiktok.com` y pégalas aquí."
            )
            cookies_editor = gr.Textbox(
                value=get_cookies_content(), label="🍪 Cookies de TikTok",
                lines=10, placeholder="Pega el contenido del archivo de cookies Netscape..."
            )
            with gr.Row():
                btn_refresh_cookies = gr.Button("🔄 Refrescar")
                btn_save_cookies    = gr.Button("💾 Guardar Cookies", variant="primary")

            gr.Markdown("---")
            gr.Markdown("### Gestion de Canales YouTube (Multi-Usuario)")
            gr.Markdown(
                "Registra uno o mas canales de YouTube. Cada canal guarda su propio token.\n"
                "Usa el mismo `client_secrets.json` de arriba para todos los canales."
            )
            with gr.Row():
                mc_nombre_input = gr.Textbox(label="Nombre del canal (sin espacios, ej: canal_principal)", placeholder="mi_canal")
                btn_mc_auth     = gr.Button("🔑 Autenticar Canal (abre navegador)", variant="primary")
            with gr.Row():
                btn_mc_estado   = gr.Button("🔄 Ver canales registrados")
                mc_canal_borrar = gr.Textbox(label="Nombre del canal a eliminar", placeholder="mi_canal")
                btn_mc_borrar   = gr.Button("🗑️ Eliminar Canal", variant="stop")

        # --- PESTAÑA 2 ---
        with gr.TabItem("2. Descargar Videos"):
            gr.Markdown("### Descargar videos de un perfil de TikTok sin marca de agua")
            gr.Markdown("Descarga los videos públicos de cualquier perfil. Las cookies de la Pestaña 1 ayudan a evitar bloqueos.")
            with gr.Row():
                username_input    = gr.Textbox(label="👤 Usuario TikTok (sin @)", placeholder="usuario")
                max_videos_slider = gr.Slider(minimum=1, maximum=100, value=20, step=1, label="Máximo de videos")
            btn_descargar = gr.Button("🚀 Iniciar Descarga", variant="primary")

        # --- PESTAÑA 3 ---
        with gr.TabItem("3. Anticopyright"):
            gr.Markdown("### Aplicar procesamiento Anti-Copyright")
            gr.Markdown(
                "Toma los videos descargados de TikTok y les aplica transformaciones "
                "sutiles de video y audio. Usa los mismos scripts del GUI principal."
            )
            ciclos_slider = gr.Slider(minimum=1, maximum=5, value=2, step=1, label="Número de ciclos de procesamiento")
            shorts_anticopy_cb = gr.Checkbox(
                label="📱 Convertir a vertical 9:16 (fondo difuminado — necesario para Shorts)", value=True
            )
            btn_anticopy  = gr.Button("🛡️ Iniciar Anticopyright", variant="primary")

        # --- PESTAÑA 4 ---
        with gr.TabItem("4. Subir a YouTube"):
            gr.Markdown("### Autenticación con YouTube API")
            gr.Markdown(
                "#### Paso 1 — Crear proyecto y credenciales en Google Cloud:\n"
                "1. Ve a **console.cloud.google.com** → crea o selecciona un proyecto\n"
                "2. **APIs y servicios → Biblioteca** → busca **YouTube Data API v3** → clic en **Habilitar** ⚠️ obligatorio\n"
                "3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth 2.0**\n"
                "4. Tipo: **Aplicación de escritorio** → nombre cualquiera (ej: `Darks Uploader`) → Crear\n"
                "5. Descarga el JSON → renómbralo `client_secrets.json`\n"
                "6. Colócalo en: `GUI_TIKTOK/proyectos_tiktok/credenciales_youtube/client_secrets.json`\n\n"
                "#### Paso 2 — Configurar pantalla de consentimiento (solo primera vez):\n"
                "1. **APIs y servicios → Pantalla de consentimiento OAuth → Comenzar**\n"
                "2. Nombre de la app: cualquiera · Correo: tu Gmail → Siguiente hasta Finalizar\n"
                "3. **Público → Usuarios externos** → Crear\n"
                "4. **Público → Usuarios de prueba → + Add users** → agrega el Gmail de tu canal → Guardar\n"
                "5. ✅ La API es **completamente gratis**, no se cobra nada.\n\n"
                "#### Paso 3 — Autenticar:\n"
                "Haz clic en el botón de abajo. Se abrirá el navegador — inicia sesión con la cuenta del canal YouTube.\n"
                "Si aparece **'Google no verificó esta app'** → clic en **Continuar** (es tu propia app, es seguro)."
            )
            with gr.Row():
                btn_auth_yt     = gr.Button("🔑 Autenticar con YouTube (abre navegador)", variant="secondary")
                btn_cambiar_canal = gr.Button("🔄 Cambiar de Canal (cerrar sesión)", variant="stop")

            gr.Markdown("---")
            gr.Markdown("### Configurar uploads automáticos")
            with gr.Row():
                titulo_input      = gr.Textbox(label="📝 Título base", placeholder="Mi video TikTok", value="Video")
                descripcion_input = gr.Textbox(label="📋 Descripción", placeholder="Descripción para todos los videos", lines=3)

            tags_input = gr.Textbox(
                label="🏷️ Tags base (separados por coma) — se combinan con tendencias de Google Trends + YouTube",
                placeholder="futbol, ecuador, gol, shorts",
                value="futbol, shorts, ecuador"
            )
            with gr.Row():
                shorts_cb = gr.Checkbox(
                    label="📱 Subir como Shorts (agrega #Shorts al título — para videos verticales < 60 seg)", value=True
                )
                modo_prueba_cb = gr.Checkbox(
                    label="🧪 Modo prueba (4 min entre uploads)", value=True
                )
                tags_modo = gr.Radio(
                    choices=["✅ Siempre con tags", "🎲 Aleatorio", "❌ Sin tags"],
                    value="🎲 Aleatorio", label="🏷️ Modo de tags"
                )

            with gr.Row():
                btn_iniciar  = gr.Button("▶️ Iniciar Scheduler", variant="primary")
                btn_detener  = gr.Button("⏹️ Detener Scheduler", variant="stop")
                btn_ver_log  = gr.Button("🔄 Ver Log del Scheduler")

        # --- PESTAÑA 5 ---
        with gr.TabItem("5. Limpieza"):
            gr.Markdown("### Limpiar carpetas de trabajo")
            cb_orig = gr.Checkbox(True,  label="🗑️ Eliminar Videos Originales (TikTok descargados)")
            cb_proc = gr.Checkbox(False, label="🗑️ Eliminar Videos Procesados (anticopyright)")
            cb_temp = gr.Checkbox(True,  label="🗑️ Eliminar carpetas temporales del anticopyright (temp_anticopy_*)")
            btn_limpiar = gr.Button("🗑️ Limpiar Seleccionadas", variant="stop")

        with gr.TabItem("6. Proceso Completo"):
            gr.Markdown("### ⚡ Descarga → Anticopyright → Subir a YouTube")
            gr.Markdown("Hace todo el proceso de una sola vez.")
            with gr.Row():
                pc_usuario = gr.Textbox(label="👤 Usuario TikTok (sin @)", placeholder="usuario")
                pc_max     = gr.Slider(minimum=1, maximum=100, value=10, step=1, label="Máx. videos")
                pc_ciclos  = gr.Slider(minimum=1, maximum=5, value=3, step=1, label="Ciclos anticopyright")
            with gr.Row():
                pc_titulo  = gr.Textbox(label="📝 Título base YouTube", value="Video")
                pc_desc    = gr.Textbox(label="📋 Descripción", lines=2)
            pc_tags = gr.Textbox(
                label="🏷️ Tags base (separados por coma)",
                placeholder="futbol, ecuador, gol, shorts",
                value="futbol, shorts, ecuador"
            )
            with gr.Row():
                pc_shorts      = gr.Checkbox(label="📱 Subir como Shorts", value=True)
                pc_vertical    = gr.Checkbox(label="📱 Convertir a vertical 9:16 (fondo difuminado)", value=True)
                pc_prueba      = gr.Checkbox(label="🧪 Modo prueba (4 min)", value=True)
                pc_tags_modo   = gr.Radio(
                    choices=["✅ Siempre con tags", "🎲 Aleatorio", "❌ Sin tags"],
                    value="🎲 Aleatorio", label="🏷️ Modo de tags"
                )
            btn_proceso_completo = gr.Button("⚡ INICIAR PROCESO COMPLETO", variant="primary")

        with gr.TabItem("7. Log de Actividad"):
            gr.Markdown("### Registro de actividad y errores")
            log_viewer = gr.Textbox(label="📋 Log", lines=20, interactive=False)
            with gr.Row():
                btn_reflog = gr.Button("🔄 Actualizar")
                btn_limlog = gr.Button("🗑️ Limpiar Log", variant="stop")

        # --- PESTAÑA 8 ---
        with gr.TabItem("8. Multi-Usuario"):
            gr.Markdown("### Descarga → Anticopyright → Subida a multiples canales")
            gr.Markdown(
                "Descarga videos de varios usuarios de TikTok, aplica anticopyright "
                "y los sube a diferentes canales de YouTube en orden alternado (round-robin).\n\n"
                "**Registra los canales primero en Pestana 1 → Gestion de Canales.**"
            )
            mu_usuarios = gr.Textbox(
                label="Usuarios TikTok (uno por linea o separados por coma)",
                placeholder="usuario1\nusuario2\nusuario3",
                lines=4
            )
            with gr.Column():
                _canales_lista  = multi_canal_auth.listar_canales()
                mu_rows      = []
                mu_checks    = []
                mu_names     = []
                mu_status    = []
                mu_auth_btns = []
                mu_del_btns  = []
                for _i in range(_MU_MAX_CANALES):
                    _def_name = _canales_lista[_i] if _i < len(_canales_lista) else f"canal_{_i + 1}"
                    with gr.Row() as _row:
                        _ch = gr.Checkbox(label="Usar", value=False)
                        _nm = gr.Textbox(value=_def_name, label=f"Canal {_i + 1}", scale=2, placeholder="Nombre del canal")
                        _st = gr.Textbox(value=_mu_get_estado(_def_name), label="Estado", interactive=False, scale=3)
                        _ab = gr.Button("🔑 Autenticar", scale=1)
                        _db = gr.Button("🗑️ Borrar token", scale=1, variant="stop")
                    mu_rows.append(_row)
                    mu_checks.append(_ch)
                    mu_names.append(_nm)
                    mu_status.append(_st)
                    mu_auth_btns.append(_ab)
                    mu_del_btns.append(_db)
                btn_mu_refresh = gr.Button("🔄 Refrescar estado")

            with gr.Row():
                mu_max    = gr.Slider(minimum=1, maximum=100, value=10, step=1, label="Videos por usuario")
                mu_rr     = gr.Slider(minimum=1, maximum=10,  value=2,  step=1, label="Videos por usuario antes de cambiar canal")
                mu_ciclos = gr.Slider(minimum=1, maximum=5,   value=2,  step=1, label="Ciclos anticopyright")
            with gr.Row():
                mu_titulo = gr.Textbox(label="Titulo base YouTube", value="Video", placeholder="Mi video")
                mu_desc   = gr.Textbox(label="Descripcion", lines=2, placeholder="Descripcion para todos los videos")
            mu_tags = gr.Textbox(
                label="Tags base (separados por coma)",
                placeholder="futbol, ecuador, shorts",
                value="futbol, shorts, ecuador"
            )
            with gr.Row():
                mu_shorts    = gr.Checkbox(label="Subir como Shorts", value=True)
                mu_prueba    = gr.Checkbox(label="Modo prueba (4 min entre subidas)", value=True)
                mu_tags_modo = gr.Radio(
                    choices=["✅ Siempre con tags", "🎲 Aleatorio", "❌ Sin tags"],
                    value="🎲 Aleatorio", label="Modo de tags"
                )
            with gr.Row():
                btn_mu_iniciar = gr.Button("⚡ INICIAR MULTI-USUARIO", variant="primary")
                btn_mu_detener = gr.Button("⏹️ Detener", variant="stop")
            mu_console = gr.Textbox(label="Consola Multi-Usuario", lines=20, interactive=False)

    # --- EVENTOS ---
    btn_crear.click(fn=crear_estructura_carpetas, outputs=output_console).then(
        fn=get_cookies_content, outputs=cookies_editor
    )
    btn_refresh_cookies.click(fn=get_cookies_content, outputs=cookies_editor)
    btn_save_cookies.click(fn=save_cookies_content, inputs=cookies_editor, outputs=output_console)
    btn_descargar.click(fn=descargar_favoritos_tiktok, inputs=[username_input, max_videos_slider], outputs=output_console)
    btn_anticopy.click(fn=iniciar_anticopyright, inputs=[ciclos_slider, shorts_anticopy_cb], outputs=output_console)
    btn_auth_yt.click(fn=autenticar_youtube_gui, outputs=output_console)
    btn_cambiar_canal.click(fn=cambiar_canal_youtube, outputs=output_console)
    btn_iniciar.click(fn=iniciar_scheduler_youtube, inputs=[modo_prueba_cb, titulo_input, descripcion_input, shorts_cb, tags_input, tags_modo], outputs=output_console)
    btn_detener.click(fn=detener_scheduler, outputs=output_console)
    btn_ver_log.click(fn=ver_log_scheduler, outputs=output_console)
    btn_limpiar.click(fn=limpiar_carpetas, inputs=[cb_orig, cb_proc, cb_temp], outputs=output_console)
    btn_proceso_completo.click(fn=proceso_completo, inputs=[pc_usuario, pc_max, pc_ciclos, pc_prueba, pc_titulo, pc_desc, pc_shorts, pc_vertical, pc_tags, pc_tags_modo], outputs=output_console)
    btn_reflog.click(fn=lambda: open(LOG_FILE, encoding='utf-8').read() if os.path.exists(LOG_FILE) else "Sin actividad aún.", outputs=log_viewer)
    btn_limlog.click(fn=lambda: open(LOG_FILE, 'w', encoding='utf-8').close() or "✅ Log limpiado.", outputs=log_viewer)

    # Eventos pestaña 1 — Gestion de canales
    btn_mc_auth.click(fn=multi_canal_auth.autenticar_canal, inputs=mc_nombre_input, outputs=output_console)
    btn_mc_estado.click(fn=multi_canal_auth.estado_canales, outputs=output_console)
    btn_mc_borrar.click(fn=multi_canal_auth.eliminar_canal, inputs=mc_canal_borrar, outputs=output_console)

    # Eventos pestaña 8 — Multi-usuario
    btn_mu_refresh.click(fn=_mu_refrescar_estados, inputs=mu_names, outputs=mu_status)
    for _i in range(_MU_MAX_CANALES):
        mu_auth_btns[_i].click(fn=_mu_autenticar_y_estado, inputs=[mu_names[_i]], outputs=[mu_console, mu_status[_i]])
        mu_del_btns[_i].click(fn=_mu_borrar_y_estado, inputs=[mu_names[_i]], outputs=[mu_console, mu_status[_i]])
    btn_mu_iniciar.click(
        fn=_mu_iniciar,
        inputs=[mu_usuarios] + mu_names + mu_checks +
               [mu_max, mu_rr, mu_ciclos, mu_prueba, mu_titulo, mu_desc, mu_shorts, mu_tags, mu_tags_modo],
        outputs=mu_console
    )
    btn_mu_detener.click(fn=multi_usuario.detener, outputs=mu_console)


if __name__ == "__main__":
    if not os.path.exists(BASE_DIR):
        print("Primera ejecución: creando estructura de carpetas...")
        crear_estructura_carpetas()
    demo.launch(theme=gr.themes.Soft())
