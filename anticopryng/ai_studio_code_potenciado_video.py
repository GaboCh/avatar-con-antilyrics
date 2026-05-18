import os
import subprocess
import random
import glob
import time
import numpy as np

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

def get_random_value(base, tolerance):
    """Genera un valor flotante aleatorio dentro de un rango."""
    return base + random.uniform(-tolerance, tolerance)

def procesar_variaciones_multimedia(crf=23, preset="medium", seed=None):
    """
    Aplica una pila de transformaciones potentes y dinámicas a cada archivo
    de video (.mp4) o audio (.mp3) para maximizar su originalidad y evitar
    la detección de contenido duplicado a largo plazo.
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
    
    # ===== PROCESAMIENTO DE ARCHIVOS MULTIMEDIA =====
    for i, src_path in enumerate(media_files):
        
        # --- BANCOS DE TRANSFORMACIONES DINÁMICAS (AJUSTADOS PARA SER SUTILES) ---
        recetas_geometricas = [
            {"name": "rot", "vf": f"rotate={get_random_value(0, 0.005)}"},
            {"name": "zoom", "vf": f"scale=iw*{get_random_value(1.005, 0.002)}:ih*{get_random_value(1.005, 0.002)},crop=iw/{get_random_value(1.005, 0.002)}:ih/{get_random_value(1.005, 0.002)}"},
        ]
        recetas_color = [
            {"name": "contraste", "vf": f"eq=contrast={get_random_value(1.005, 0.005)}:brightness={get_random_value(0, -0.005)}"},
            {"name": "saturacion", "vf": f"eq=saturation={get_random_value(1.02, 0.01)}"},
            {"name": "balance_color", "vf": f"colorbalance=rs={get_random_value(0, 0.01)}:bs={get_random_value(0, 0.01)}"}
        ]
        recetas_ruido_video = [
            {"name": "grano_sutil", "vf": "noise=alls=1:allf=t+u"},
        ]
        recetas_audio_mejoradas = [
            {"name": "pitch_up", "af": f"asetrate=44100*{get_random_value(1.005, 0.003)},aresample=44100"},
            {"name": "pitch_down", "af": f"asetrate=44100*{get_random_value(0.995, 0.003)},aresample=44100"},
            {"name": "tempo_rapido", "af": f"atempo={get_random_value(1.008, 0.004)}"},
            {"name": "tempo_lento", "af": f"atempo={get_random_value(0.992, 0.004)}"},
            {"name": "boost_eq", "af": f"equalizer=f={random.randint(100, 6000)}:width_type=h:width=200:g={random.randint(1, 2)}"},
            {"name": "combo_aleatorio", "af": f"atempo={get_random_value(1.005, 0.002)},asetrate=44100*{get_random_value(1.003, 0.002)},aresample=44100"},
        ]

        long_base_name = os.path.splitext(os.path.basename(src_path))[0]
        # ### CORRECCIÓN CLAVE ###
        # Para evitar nombres de archivo que superen el límite de Windows,
        # tomamos solo la parte original del nombre (antes del primer "_").
        # Así, "1_recetaA_recetaB" se convierte de nuevo en "1".
        base_name = long_base_name.split('_')[0]

        extension = os.path.splitext(src_path)[1].lower()
        cmd, recipe_name, dst_path = [], "", ""

        print(f"\nProcesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        audio_recipe = random.choice(recetas_audio_mejoradas)
        af_chain = audio_recipe['af']
        
        ruido_path = os.path.join(PROJECT_DIR, "ruido.mp3")
        aplicar_ruido = random.choice([True, True, False])

        if extension == ".mp4":
            geo = random.choice(recetas_geometricas)
            color = random.choice(recetas_color)
            ruido_vid = random.choice(recetas_ruido_video) if recetas_ruido_video else {"name": "sin_ruido", "vf": ""}
            
            # --- LÍNEAS NUEVAS ---
            vf_chain = f"setsar=1,{geo['vf']},{color['vf']}"
            if ruido_vid["vf"]: # Solo añade la coma y el filtro si existe
                vf_chain += f",{ruido_vid['vf']}"

            # Filtros de seguridad: 1. Asegura dimensiones pares. 2. Asegura un ancho mínimo de 720px.
            vf_chain += ",crop=floor(iw/2)*2:floor(ih/2)*2,scale=w='max(iw,720)':h=-2"
            recipe_name = f"{geo['name']}_{color['name']}_{ruido_vid['name']}_{audio_recipe['name']}"
            dst_path = os.path.join(salida_dir, f"{base_name}_{recipe_name}.mp4")

            if os.path.exists(ruido_path) and aplicar_ruido:
                af_chain_complex = f"[0:a]{af_chain},volume=1.0[main];[1:a]volume={get_random_value(0.015, 0.005)},aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first[a]"
                recipe_name += "_con_ruido"
                dst_path = os.path.join(salida_dir, f"{base_name}_{recipe_name}.mp4")
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path, "-i", ruido_path,
                    "-filter_complex", f"[0:v]{vf_chain},format=yuv420p[v];{af_chain_complex}",
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-map_metadata", "-1",
                    dst_path
                ]
            else:
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-vf", vf_chain, "-af", af_chain,
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-map_metadata", "-1",
                    dst_path
                ]
        
        elif extension == ".mp3":
            # La lógica de MP3 también se beneficia de no tener nombres largos
            dst_path = os.path.join(salida_dir, f"{base_name}_{audio_recipe['name']}.mp3")
            cmd_base = [ffmpeg_cmd, "-y", "-i", src_path]
            
            if os.path.exists(ruido_path) and aplicar_ruido:
                af_chain_complex = f"[0:a]{af_chain},volume=1.0[main];[1:a]volume={get_random_value(0.015, 0.005)},aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first[a]"
                dst_path = os.path.join(salida_dir, f"{base_name}_{audio_recipe['name']}_con_ruido.mp3")
                cmd = cmd_base + ["-i", ruido_path, "-filter_complex", af_chain_complex, "-c:a", "libmp3lame", "-b:a", "192k", "-map_metadata", "-1", dst_path]
            else:
                cmd = cmd_base + ["-af", af_chain, "-c:a", "libmp3lame", "-b:a", "192k", "-map_metadata", "-1", dst_path]
        else:
            print(f"Saltando formato no soportado: {os.path.basename(src_path)}")
            continue

        try:
            print(f"    Aplicando receta: [{os.path.basename(dst_path)}]")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"Archivo generado: {os.path.basename(dst_path)}")
        except subprocess.CalledProcessError as e:
            print(f"Error de FFmpeg procesando {os.path.basename(src_path)}")
            print(f"   Mensaje de FFmpeg: {e.stderr.decode(errors='ignore')}")
        except Exception as e:
            print(f"Error inesperado: {e}")

    print(f"\nProceso completado. Archivos guardados en: {salida_dir}")

# --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    print("==============================================")
    print("=== INICIO DEL SCRIPT ANTI-COPYRIGHT AVANZADO ===")
    print("==============================================")
    
    procesar_variaciones_multimedia(crf=24, preset="fast")
    
    print("\n==============================================")
    print("=== SCRIPT FINALIZADO ===")
    print("==============================================")