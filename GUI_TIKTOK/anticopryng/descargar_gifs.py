import os
import urllib.request

base_dir = r"C:\IA\funcional\avatar_srt\avatar\GUI_TIKTOK\anticopryng"
webm_dir = os.path.join(base_dir, "recursos_webm")
os.makedirs(webm_dir, exist_ok=True)

# Enlaces directos a GIFs con fondo transparente (dominio publico para pruebas)
urls = [
    ("tierra_girando.gif", "https://upload.wikimedia.org/wikipedia/commons/2/2c/Rotating_earth_%28large%29.gif"),
    ("cargando.gif", "https://upload.wikimedia.org/wikipedia/commons/d/de/Ajax-loader.gif"),
    ("spinner.gif", "https://upload.wikimedia.org/wikipedia/commons/a/a2/Spinner_font_awesome.gif")
]

print("Descargando GIFs transparentes de prueba...")
for nombre, url in urls:
    ruta = os.path.join(webm_dir, nombre)
    try:
        urllib.request.urlretrieve(url, ruta)
        print(f"[OK] Descargado: {nombre}")
    except Exception as e:
        print(f"[ERROR] No se pudo descargar {nombre}: {e}")

print("¡Listo! Revisa la carpeta recursos_webm")
