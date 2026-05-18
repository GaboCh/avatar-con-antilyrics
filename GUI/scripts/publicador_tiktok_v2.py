import os
import time
try:
    from tiktok_uploader.upload import upload_video
except ImportError:
    upload_video = None

def publicar_video_tiktok(video_path, descripcion, session_id=None, log_func=print):
    """
    Sube un video a TikTok utilizando el archivo de cookies Netscape.
    """
    if not os.path.exists(video_path):
        return f"❌ El archivo no existe: {video_path}"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    gui_dir = os.path.dirname(script_dir)
    cookies_path = os.path.join(gui_dir, 'proyectos_gui', 'swap', 'cookies', 'www.tiktok.com_cookies.txt')

    if not os.path.exists(cookies_path):
        return f"❌ Error: No se encontró el archivo de cookies en {cookies_path}"

    if upload_video is None:
        return "❌ Error: La librería 'tiktok-uploader' no está instalada. Ejecuta: pip install tiktok-uploader"

    log_func(f"🚀 Iniciando subida REAL a TikTok: {os.path.basename(video_path)}")
    log_func(f"🍪 Usando cookies de: {cookies_path}")
    log_func("⚠️  ATENCIÓN: Se abrirá una ventana de Chrome. Si aparece un cartel de 'Entendido' o 'Got it', POR FAVOR DALE CLIC manualmente para que el proceso continúe.")

    try:
        # Intentamos la subida. headless=False hace visible la ventana.
        upload_video(
            video_path,
            description=descripcion,
            cookies=cookies_path,
            browser='chrome',
            headless=False
        )
        return f"✅ Video subido correctamente a TikTok: {os.path.basename(video_path)}"

    except Exception as e:
        return f"❌ Error durante la publicación en TikTok: {str(e)}"
