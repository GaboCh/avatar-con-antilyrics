import os
import subprocess
import glob
import sys

def descargar_videos_usuario(ig_user, max_videos=5, output_dir=None, log_func=print):
    """
    Descarga videos basándose en el archivo url.txt que el usuario alimenta manualmente.
    Esta es la solución súper robusta que toma los beneficios de la nueva automatización
    pero usa la fiabilidad probada de la Pestaña 2.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gui_dir = os.path.dirname(script_dir)
    
    if not output_dir:
        output_dir = os.path.join(gui_dir, 'proyectos_gui', 'swap', 'videos_originales')
    
    url_file = os.path.join(gui_dir, 'proyectos_gui', 'swap', 'url', 'url.txt')
    cookies_path = os.path.join(gui_dir, 'proyectos_gui', 'swap', 'cookies', 'www.instagram.com_cookies.txt')
    
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(url_file):
        log_func(f"❌ No se encontró el archivo de URLs: {url_file}")
        return []

    urls = []
    with open(url_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
    
    if not urls:
        log_func("⚠️ El archivo url.txt está vacío. Pega las URLs de Instagram en la Pestaña 1.")
        return []

    # Limitamos al máximo solicitado (por seguridad)
    urls_a_descargar = urls[:max_videos]
    log_func(f"🎬 Se descargarán {len(urls_a_descargar)} videos basados en {url_file}")
    
    videos_descargados = []
    
    for i, url in enumerate(urls_a_descargar, 1):
        log_func(f"\n📥 Descargando video {i}/{len(urls_a_descargar)}...")
        log_func(f"🔗 URL: {url}")
        
        # Mismo comando que usa la Pestaña 2 (el que ya funciona)
        cmd = [
            'yt-dlp', url,
            '--format', 'mp4/best',
            '--output', os.path.join(output_dir, f'video_v2_%(id)s.%(ext)s'),
            '--no-warnings', '--no-playlist',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--add-header', 'Accept-Language:en-US,en;q=0.9,es;q=0.8',
            '--add-header', 'Referer:https://www.instagram.com/',
            '--extractor-retries', '5', '--socket-timeout', '30',
            '--sleep-interval', '3', '--max-sleep-interval', '8',
        ]
        
        if os.path.exists(cookies_path):
            cmd.extend(['--cookies', cookies_path])

        archivos_antes = set(glob.glob(os.path.join(output_dir, '*.mp4')))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            archivos_despues = set(glob.glob(os.path.join(output_dir, '*.mp4')))
            nuevos = list(archivos_despues - archivos_antes)

            if result.returncode == 0 and nuevos:
                videos_descargados.append(nuevos[0])
                log_func(f"✅ Video descargado con éxito: {os.path.basename(nuevos[0])}")
            else:
                log_func(f"❌ Error al descargar este video: {result.stderr.strip()[:100]}")
        except Exception as e:
            log_func(f"❌ Error inesperado: {e}")

    log_func(f"\n🏁 Proceso de descarga finalizado. {len(videos_descargados)} videos listos.")
    return videos_descargados
