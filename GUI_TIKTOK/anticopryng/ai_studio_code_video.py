import os
import subprocess
import random
import glob
import time
import sys  # Importar sys para leer los argumentos de la línea de comandos

# =========================================================================
# === SCRIPT TRABAJADOR: MODIFICADO PARA SER PORTABLE ===
# Este script ya no se ejecuta directamente. Es llamado por 'app_video.py'.
# Recibe la carpeta de entrada y salida como argumentos.
# =========================================================================


# --- CONFIGURACIÓN PRINCIPAL ---
# La ruta del proyecto ahora solo se usa para encontrar recursos locales
# como 'ruido.mp3', que debe estar en la misma carpeta que este script.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def detectar_encoder(ffmpeg_cmd):
    """Detecta el mejor encoder disponible: NVIDIA > AMD > Intel > CPU."""
    candidatos = [
        ("h264_nvenc", "GPU NVIDIA"),
        ("h264_amf",   "GPU AMD"),
        ("h264_qsv",   "GPU Intel"),
    ]
    for encoder, nombre in candidatos:
        try:
            r = subprocess.run([
                ffmpeg_cmd, "-y",
                "-f", "lavfi", "-i", "color=c=black:s=640x480:r=25:d=1",
                "-c:v", encoder, "-frames:v", "25",
                "-f", "null", "-"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode == 0:
                print(f"{nombre} funcional — usando {encoder}")
                return encoder
        except Exception:
            pass

    print("GPU no disponible — usando libx264 (CPU)")
    return "libx264"


def procesar_variaciones_multimedia(entrada_dir, salida_dir, crf=21, preset="medium", seed=None):
    """
    Aplica una pila de transformaciones a cada archivo multimedia.
    Ahora recibe las carpetas de entrada y salida como parámetros.
    """
    if seed is None:
        random.seed(time.time())
    else:
        random.seed(seed)

    # --- Los directorios ahora son argumentos de la función ---
    print(f"Asegurando que la carpeta de salida exista: {salida_dir}")
    os.makedirs(salida_dir, exist_ok=True)
    
    # --- Lógica de búsqueda de FFmpeg ---
    ffmpeg_cmd = None
    print("\nBuscando FFmpeg local...")
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        if not os.path.exists(ffmpeg_cmd):
            ffmpeg_cmd = None
            print("FFmpeg ejecutable no encontrado en la ruta esperada.")
        else:
            print(f"FFmpeg encontrado en: {ffmpeg_cmd}")
    except ImportError:
         print("Error: La librería 'imageio-ffmpeg' no está instalada.")
    except Exception as e:
        print(f"Error al localizar FFmpeg: {e}")

    if not ffmpeg_cmd:
        print("\nERROR FATAL: No se pudo encontrar FFmpeg local. El script no puede continuar.")
        return
    encoder = detectar_encoder(ffmpeg_cmd)
        
    # --- Búsqueda de archivos multimedia en la carpeta de entrada proporcionada ---
    print(f"\nBuscando archivos multimedia en: {entrada_dir}")
    media_files = sorted(glob.glob(os.path.join(entrada_dir, "*.mp4"))) + \
                  sorted(glob.glob(os.path.join(entrada_dir, "*.mp3")))

    if not media_files:
        print(f"No se encontraron archivos en '{entrada_dir}'.")
        return

    print(f"Iniciando postprocesamiento de {len(media_files)} archivos multimedia...")

    # ===== BANCOS DE TRANSFORMACIONES (SUTILES) =====
    recetas_geometricas = [
        {"name": "rot_izq", "vf": "rotate=-0.005"}, {"name": "rot_der", "vf": "rotate=0.005"},
        {"name": "zoom_ligero", "vf": "scale=iw*1.005:ih*1.005,crop=iw/1.005:ih/1.005"},
    ]
    recetas_color = [
        {"name": "contraste_alto", "vf": "eq=contrast=1.005:brightness=-0.005"},
        {"name": "contraste_bajo", "vf": "eq=contrast=0.995:brightness=0.005"},
        {"name": "saturacion_alta", "vf": "eq=saturation=1.02"},
        {"name": "calido", "vf": "colorbalance=rs=0.01"}, {"name": "frio", "vf": "colorbalance=bs=0.01"}
    ]
    _r_up    = round(random.uniform(1.01, 1.0299), 4)
    _r_down  = round(random.uniform(0.9701, 0.99), 4)
    _r_combo = round(random.uniform(1.01, 1.025), 4)
    _t_rap   = round(random.uniform(1.01, 1.03), 4)
    _t_len   = round(random.uniform(0.97, 0.99), 4)
    _t_combo = round(random.uniform(1.01, 1.025), 4)
    recetas_audio_mejoradas = [
        {"name": "pitch_up",         "af": f"asetrate=44100*{_r_up},aresample=44100,atempo={round(1/_r_up, 4)}"},
        {"name": "pitch_down",       "af": f"asetrate=44100*{_r_down},aresample=44100,atempo={round(1/_r_down, 4)}"},
        {"name": "tempo_rapido",     "af": f"atempo={_t_rap}",  "vf_extra": f"setpts=PTS/{_t_rap}"},
        {"name": "tempo_lento",      "af": f"atempo={_t_len}",  "vf_extra": f"setpts=PTS/{_t_len}"},
        {"name": "bass_boost",       "af": "equalizer=f=60:width_type=h:width=20:g=2"},
        {"name": "treble_boost",     "af": "equalizer=f=8000:width_type=h:width=2000:g=2"},
        {"name": "pitch_tempo_combo","af": f"atempo={_t_combo},asetrate=44100*{_r_combo},aresample=44100,atempo={round(1/_r_combo, 4)}", "vf_extra": f"setpts=PTS/{_t_combo}"},
    ]

    # ===== PROCESAMIENTO DE ARCHIVOS MULTIMEDIA =====
    for i, src_path in enumerate(media_files):
        base_name = os.path.splitext(os.path.basename(src_path))[0].split('__')[0]
        extension = os.path.splitext(src_path)[1].lower()
        cmd, recipe_name, dst_path = [], "", ""

        print(f"\nProcesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        audio_recipe = random.choice(recetas_audio_mejoradas)
        af_chain = audio_recipe['af']
        
        ruido_path = os.path.join(PROJECT_DIR, "ruido.mp3")
        aplicar_ruido = random.choice([True, False])
        
        if os.path.exists(ruido_path) and aplicar_ruido and extension == ".mp3":
            af_chain_complex = f"[0:a]{af_chain}[main];[1:a]volume=0.015,aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first"
            recipe_name = audio_recipe['name'] + "_con_ruido"
        else:
            af_chain_complex = None
            recipe_name = audio_recipe['name']

        if extension == ".mp4":
            geo = random.choice(recetas_geometricas)
            color = random.choice(recetas_color)
            _vf_pre  = audio_recipe.get('vf_extra', '')
            vf_chain = f"{_vf_pre + ',' if _vf_pre else ''}setsar=1,{geo['vf']},{color['vf']},crop=floor(iw/2)*2:floor(ih/2)*2,scale=w='max(iw,720)':h=-2"
            recipe_name = f"{geo['name']}_{color['name']}_{audio_recipe['name']}"
            dst_path = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp4")

            if encoder == "h264_nvenc":
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-vf", vf_chain, "-af", af_chain,
                    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", dst_path
                ]
            else:
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-vf", vf_chain, "-af", af_chain,
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", dst_path
                ]
        
        elif extension == ".mp3":
            dst_path = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp3")
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
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Archivo generado: {os.path.basename(dst_path)}")
        except subprocess.CalledProcessError as e:
            print(f"Error de FFmpeg procesando {os.path.basename(src_path)}")
            # Propagar el error para que el script principal lo capture
            raise e
        except Exception as e:
            print(f"Error inesperado: {e}")
            raise e

    print(f"\nProceso completado. Archivos guardados en: {salida_dir}")

# --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    # Verifica que se hayan pasado los argumentos correctos
    if len(sys.argv) != 3:
        print("Uso: python ai_studio_code_video.py <ruta_carpeta_entrada> <ruta_carpeta_salida>")
        sys.exit(1)

    # Asigna los argumentos a las variables
    entrada_dir_arg = sys.argv[1]
    salida_dir_arg = sys.argv[2]
    
    print("==============================================")
    print("=== INICIO DEL SCRIPT TRABAJADOR (NORMAL) ===")
    print("==============================================")
    
    # Llama a la función principal con los argumentos recibidos
    procesar_variaciones_multimedia(entrada_dir_arg, salida_dir_arg, crf=23, preset="fast")
    
    print("\n==============================================")
    print("=== SCRIPT TRABAJADOR (NORMAL) FINALIZADO ===")
    print("==============================================")