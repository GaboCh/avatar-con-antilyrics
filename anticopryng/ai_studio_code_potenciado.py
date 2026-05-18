# app.py

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
#    Esta es la técnica más potente para evitar la detección de copyright.
# 4. Coloca tus archivos MP4 y MP3 en la carpeta 'videos_finales'.
# 5. Ejecuta el script: python app.py
# =========================================================================


# --- CONFIGURACIÓN PRINCIPAL ---
# Define el directorio base del proyecto.
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
    
    print(f" Asegurando que las carpetas existan en: {PROJECT_DIR}")
    os.makedirs(entrada_dir, exist_ok=True)
    os.makedirs(salida_dir, exist_ok=True)
    print(f" Carpetas creadas/verificadas: '{os.path.basename(entrada_dir)}', '{os.path.basename(salida_dir)}'")

    # --- Lógica de búsqueda de FFmpeg ---
    # (Sin cambios en esta sección)
    ffmpeg_cmd, ffprobe_cmd = None, None
    print("\n Buscando FFmpeg local dentro del entorno virtual...")
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        ffprobe_path = ffmpeg_cmd.replace("ffmpeg-win64-v4.2.2.exe", "ffprobe.exe").replace("ffmpeg.exe", "ffprobe.exe")
        if os.path.exists(ffmpeg_cmd) and os.path.exists(ffprobe_path):
            ffprobe_cmd = ffprobe_path
            print(f" FFmpeg encontrado en: {ffmpeg_cmd}")
        else:
            ffmpeg_cmd = None
            print(f" No se encontró ffprobe.exe junto a {ffmpeg_cmd}")
    except ImportError:
         print(" Error: La librería 'imageio-ffmpeg' no está instalada en el entorno. Por favor, ejecuta: pip install imageio-ffmpeg")
    except Exception as e:
        print(f" Error al localizar FFmpeg: {e}")

    if not ffmpeg_cmd or not ffprobe_cmd:
        print("\n ERROR FATAL: No se pudo encontrar FFmpeg local. El script no puede continuar.")
        return
        
    # --- Búsqueda de archivos multimedia ---
    print(f"\n Buscando archivos .mp4 y .mp3 en: {entrada_dir}")
    media_files = sorted(glob.glob(os.path.join(entrada_dir, "*.mp4"))) + \
                  sorted(glob.glob(os.path.join(entrada_dir, "*.mp3")))

    if not media_files:
        print(f" No se encontraron archivos en '{entrada_dir}'.")
        return

    print(f" Iniciando postprocesamiento de {len(media_files)} archivos multimedia...")

    # ===== BANCOS DE TRANSFORMACIONES DINÁMICAS (NIVEL DIOS) =====
    # ¡NUEVO! Ahora los valores no son fijos, son rangos aleatorios.
    recetas_geometricas = [
        {"name": "rot", "vf": f"rotate={get_random_value(0, 0.01)}"},
        {"name": "zoom", "vf": f"scale=iw*{get_random_value(1.01, 0.005)}:ih*{get_random_value(1.01, 0.005)},crop=iw/{get_random_value(1.01, 0.005)}:ih/{get_random_value(1.01, 0.005)}"},
        {"name": "flip_h", "vf": "hflip"}
    ]
    recetas_color = [
        {"name": "contraste", "vf": f"eq=contrast={get_random_value(1.01, 0.01)}:brightness={get_random_value(0, -0.005)}"},
        {"name": "saturacion", "vf": f"eq=saturation={get_random_value(1.05, 0.02)}"},
        {"name": "balance_color", "vf": f"colorbalance=rs={get_random_value(0, 0.02)}:bs={get_random_value(0, 0.02)}"}
    ]
    # ¡NUEVO! Añadimos grano/ruido de video para romper patrones.
    recetas_ruido_video = [
        {"name": "grano_sutil", "vf": "noise=alls=1:allf=t+u"},
        {"name": "blur_ligero", "vf": "gblur=sigma=0.1"}
    ]
    
    # Recetas de audio con parámetros dinámicos para máxima evasión.
    recetas_audio_mejoradas = [
        {"name": "pitch_up", "af": f"asetrate=44100*{get_random_value(1.03, 0.01)},aresample=44100"},
        {"name": "pitch_down", "af": f"asetrate=44100*{get_random_value(0.97, 0.01)},aresample=44100"},
        {"name": "tempo_rapido", "af": f"atempo={get_random_value(1.04, 0.01)}"},
        {"name": "tempo_lento", "af": f"atempo={get_random_value(0.96, 0.01)}"},
        {"name": "boost_eq", "af": f"equalizer=f={random.randint(60, 8000)}:width_type=h:width=200:g={random.randint(2, 4)}"},
        {"name": "efecto_radio", "af": "highpass=f=300,lowpass=f=3000"},
        {"name": "combo_aleatorio", "af": f"atempo={get_random_value(1.02, 0.01)},asetrate=44100*{get_random_value(1.01, 0.01)},aresample=44100"},
    ]

    # ===== PROCESAMIENTO DE ARCHIVOS MULTIMEDIA =====
    for i, src_path in enumerate(media_files):
        # Tomar solo el nombre original (antes de cualquier sufijo de receta)
        raw_name = os.path.splitext(os.path.basename(src_path))[0]
        base_name = raw_name.split('__')[0][:60]  # Max 60 chars, nombre limpio
        extension = os.path.splitext(src_path)[1].lower()
        cmd, recipe_name, dst_path = [], "", ""

        print(f"\n Procesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        audio_recipe = random.choice(recetas_audio_mejoradas)
        af_chain = audio_recipe['af']
        
        ruido_path = os.path.join(PROJECT_DIR, "ruido.mp3")
        aplicar_ruido = random.choice([True, True, False]) # 70% de probabilidad para mayor potencia
        
        if extension == ".mp4":
            geo = random.choice(recetas_geometricas)
            color = random.choice(recetas_color)
            ruido_vid = random.choice(recetas_ruido_video)
            
            vf_chain = f"setsar=1,{geo['vf']},{color['vf']},{ruido_vid['vf']}"
            recipe_name = f"{geo['name']}_{color['name']}_{ruido_vid['name']}_{audio_recipe['name']}"
            dst_path = os.path.join(salida_dir, f"{base_name}_{recipe_name}.mp4")

            # ¡MEJORA CLAVE! Ahora aplicamos la mezcla de ruido también a los videos MP4.
            if os.path.exists(ruido_path) and aplicar_ruido:
                af_chain_complex = f"[0:a]{af_chain},volume=1.0[main];[1:a]volume={get_random_value(0.02, 0.01)},aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first"
                recipe_name += "_con_ruido"
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path, "-i", ruido_path,
                    "-filter_complex", f"[0:v]{vf_chain}[v];{af_chain_complex}",
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-map_metadata", "-1", # ¡MEJORA CLAVE! Elimina todos los metadatos.
                    dst_path
                ]
            else:
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-vf", vf_chain, "-af", af_chain,
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-map_metadata", "-1", # ¡MEJORA CLAVE! Elimina todos los metadatos.
                    dst_path
                ]
        
        elif extension == ".mp3":
            dst_path = os.path.join(salida_dir, f"{base_name}_{audio_recipe['name']}.mp3")
            cmd_base = [ffmpeg_cmd, "-y", "-i", src_path]
            
            if os.path.exists(ruido_path) and aplicar_ruido:
                af_chain_complex = f"[0:a]{af_chain},volume=1.0[main];[1:a]volume={get_random_value(0.02, 0.01)},aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first"
                dst_path = os.path.join(salida_dir, f"{base_name}_{audio_recipe['name']}_con_ruido.mp3")
                cmd = cmd_base + ["-i", ruido_path, "-filter_complex", af_chain_complex, "-c:a", "libmp3lame", "-b:a", "192k", "-map_metadata", "-1", dst_path]
            else:
                cmd = cmd_base + ["-af", af_chain, "-c:a", "libmp3lame", "-b:a", "192k", "-map_metadata", "-1", dst_path]
        else:
            print(f" Saltando formato no soportado: {os.path.basename(src_path)}")
            continue

        try:
            print(f"    Aplicando receta: [{os.path.basename(dst_path)}]")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f" Archivo generado: {os.path.basename(dst_path)}")
        except subprocess.CalledProcessError as e:
            print(f" Error de FFmpeg procesando {os.path.basename(src_path)}")
            print(f"   Mensaje de FFmpeg: {e.stderr.decode()}")
        except Exception as e:
            print(f" Error inesperado: {e}")

    print(f"\n Proceso completado. Archivos guardados en: {salida_dir}")

# --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    print("==============================================")
    print("=== INICIO DEL SCRIPT ANTI-COPYRIGHT AVANZADO ===")
    print("==============================================")
    
    procesar_variaciones_multimedia(crf=24, preset="fast")
    
    print("\n==============================================")
    print("=== SCRIPT FINALIZADO ===")
    print("==============================================")