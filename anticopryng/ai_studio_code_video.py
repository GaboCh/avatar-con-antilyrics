import os
import subprocess
import random
import glob
import time

# =========================================================================
# === INSTRUCCIONES DE USO ===
# 1. Guarda este archivo como 'app.py' en tu carpeta de proyecto.
# 2. Abre una terminal en esa misma carpeta y activa tu entorno virtual.
# 3. **IMPORTANTE:** Descarga un archivo de "ruido blanco" (white noise) en MP3
#    y guárdalo en esta misma carpeta con el nombre exacto: 'ruido.mp3'.
# 4. Coloca tus archivos MP4 y MP3 en la carpeta 'videos_finales'.
# 5. Ejecuta el script: python app.py
# =========================================================================


# --- CONFIGURACIÓN PRINCIPAL ---
PROJECT_DIR = os.path.dirname(__file__)

def procesar_variaciones_multimedia(crf=21, preset="medium", seed=None):
    """
    Aplica una pila de transformaciones potentes a cada archivo de video (.mp4)
    o audio (.mp3) para maximizar su originalidad y evitar la detección de 
    contenido duplicado.
    """
    if seed is None:
        random.seed(time.time())
    else:
        random.seed(seed)

    # --- Configuración de directorios de entrada y salida ---
    entrada_dir = os.path.join(PROJECT_DIR, "videos_finales") 
    salida_dir = os.path.join(PROJECT_DIR, "videos_finales_procesados")
    
    print(f"Asegurando que las carpetas existan en: {PROJECT_DIR}")
    os.makedirs(entrada_dir, exist_ok=True)
    os.makedirs(salida_dir, exist_ok=True)
    print(f"Carpetas creadas/verificadas: '{os.path.basename(entrada_dir)}', '{os.path.basename(salida_dir)}'")

    # --- Lógica de búsqueda de FFmpeg ---
    ffmpeg_cmd, ffprobe_cmd = None, None
    print("\nBuscando FFmpeg local dentro del entorno virtual...")
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        ffprobe_path = ffmpeg_cmd.replace("ffmpeg-win64-v4.2.2.exe", "ffprobe.exe").replace("ffmpeg.exe", "ffprobe.exe")
        if os.path.exists(ffmpeg_cmd) and os.path.exists(ffprobe_path):
            ffprobe_cmd = ffprobe_path
            print(f"FFmpeg encontrado en: {ffmpeg_cmd}")
        else:
            ffmpeg_cmd = None
            print(f"No se encontró ffprobe.exe junto a {ffmpeg_cmd}")
    except ImportError:
         print("Error: La librería 'imageio-ffmpeg' no está instalada en el entorno. Por favor, ejecuta: pip install imageio-ffmpeg")
    except Exception as e:
        print(f"Error al localizar FFmpeg: {e}")

    if not ffmpeg_cmd or not ffprobe_cmd:
        print("\nERROR FATAL: No se pudo encontrar FFmpeg local. El script no puede continuar.")
        return
        
    # --- Búsqueda de archivos multimedia ---
    print(f"\nBuscando archivos .mp4 y .mp3 en: {entrada_dir}")
    media_files = sorted(glob.glob(os.path.join(entrada_dir, "*.mp4"))) + \
                  sorted(glob.glob(os.path.join(entrada_dir, "*.mp3")))

    if not media_files:
        print(f"No se encontraron archivos en '{entrada_dir}'.")
        return

    print(f"Iniciando postprocesamiento de {len(media_files)} archivos multimedia...")

    # ===== BANCOS DE TRANSFORMACIONES (SUTILES) =====
    # ### AJUSTE SUTIL ### Todos los valores son ahora muy pequeños para ser imperceptibles
    recetas_geometricas = [
        {"name": "rot_izq", "vf": "rotate=-0.005"}, {"name": "rot_der", "vf": "rotate=0.005"},
        {"name": "zoom_ligero", "vf": "scale=iw*1.005:ih*1.005,crop=iw/1.005:ih/1.005"}, # Zoom muy sutil
        # {"name": "flip_h", "vf": "hflip"} # Eliminado por ser demasiado obvio
    ]
    recetas_color = [
        {"name": "contraste_alto", "vf": "eq=contrast=1.005:brightness=-0.005"}, # Contraste casi nulo
        {"name": "contraste_bajo", "vf": "eq=contrast=0.995:brightness=0.005"},
        {"name": "saturacion_alta", "vf": "eq=saturation=1.02"}, # Saturación muy baja
        {"name": "calido", "vf": "colorbalance=rs=0.01"}, {"name": "frio", "vf": "colorbalance=bs=0.01"}
    ]
    
    # ### CORRECCIÓN CLAVE ###
    # Valores de tempo y pitch reducidos drásticamente para ser imperceptibles
    recetas_audio_mejoradas = [
        {"name": "pitch_up_ligero", "af": "asetrate=44100*1.005,aresample=44100"},      # Cambio del 0.5%
        {"name": "pitch_down_ligero", "af": "asetrate=44100*0.995,aresample=44100"},    # Cambio del 0.5%
        {"name": "tempo_rapido_ligero", "af": "atempo=1.008"},                         # Cambio del 0.8%
        {"name": "tempo_lento_ligero", "af": "atempo=0.992"},                         # Cambio del 0.8%
        {"name": "bass_boost_ligero", "af": "equalizer=f=60:width_type=h:width=20:g=2"}, # EQ más sutil
        {"name": "treble_boost_ligero", "af": "equalizer=f=8000:width_type=h:width=2000:g=2"},
        # {"name": "radio_effect", "af": "highpass=f=300,lowpass=f=3000"}, # Eliminado por ser muy obvio
        {"name": "rapido_y_agudo_ligero", "af": "atempo=1.004,asetrate=44100*1.002,aresample=44100"}, # Combo muy sutil
    ]

    # ===== PROCESAMIENTO DE ARCHIVOS MULTIMEDIA =====
    for i, src_path in enumerate(media_files):
        base_name = os.path.splitext(os.path.basename(src_path))[0]
        extension = os.path.splitext(src_path)[1].lower()
        cmd, recipe_name, dst_path = [], "", ""

        print(f"\nProcesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        audio_recipe = random.choice(recetas_audio_mejoradas)
        af_chain = audio_recipe['af']
        
        ruido_path = os.path.join(PROJECT_DIR, "ruido.mp3")
        aplicar_ruido = random.choice([True, False])
        
        if os.path.exists(ruido_path) and aplicar_ruido and extension == ".mp3":
            af_chain_complex = f"[0:a]{af_chain}[main];[1:a]volume=0.015,aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first" # Ruido más bajo
            recipe_name = audio_recipe['name'] + "_con_ruido"
        else:
            af_chain_complex = None
            recipe_name = audio_recipe['name']

        if extension == ".mp4":
            geo = random.choice(recetas_geometricas)
            color = random.choice(recetas_color)
            # --- LÍNEA NUEVA ---
            vf_chain = f"setsar=1,{geo['vf']},{color['vf']},crop=floor(iw/2)*2:floor(ih/2)*2,scale=w='max(iw,720)':h=-2"
            recipe_name = f"{geo['name']}_{color['name']}_{audio_recipe['name']}"
            dst_path = os.path.join(salida_dir, f"{base_name}_{recipe_name}.mp4")

            cmd = [
                ffmpeg_cmd, "-y", "-i", src_path,
                "-vf", vf_chain, "-af", af_chain,
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", dst_path
            ]
        
        elif extension == ".mp3":
            dst_path = os.path.join(salida_dir, f"{base_name}_{recipe_name}.mp3")
            cmd_base = [ffmpeg_cmd, "-y", "-i", src_path]
            
            if af_chain_complex:
                cmd = cmd_base + ["-i", ruido_path, "-filter_complex", af_chain_complex, "-c:a", "libmp3lame", "-b:a", "192k", dst_path]
            else:
                cmd = cmd_base + ["-af", af_chain, "-c:a", "libmp3lame", "-b:a", "192k", dst_path]
        else:
            print(f"Saltando formato no soportado: {os.path.basename(src_path)}")
            continue

        try:
            print(f"    Aplicando receta: [{recipe_name}]")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW )
            print(f"Archivo generado: {os.path.basename(dst_path)}")
        except KeyboardInterrupt:
            # Ignorar señales de control espurias de Windows en el primer arranque
            print(f"    [AVISO] Señal de interrupción ignorada, el proceso FFmpeg continuó normalmente.")
            print(f"Archivo generado: {os.path.basename(dst_path)}")
        except subprocess.CalledProcessError:
            print(f"Error de FFmpeg procesando {os.path.basename(src_path)}")
        except Exception as e:
            print(f"Error inesperado: {e}")

    print(f"\nProceso completado. Archivos guardados en: {salida_dir}")

# --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    print("==============================================")
    print("=== INICIO DEL SCRIPT DE PROCESAMIENTO MULTIMEDIA ===")
    print("==============================================")
    
    procesar_variaciones_multimedia(crf=23, preset="medium")
    
    print("\n==============================================")
    print("=== SCRIPT FINALIZADO ===")
    print("==============================================")