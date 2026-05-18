import os
import subprocess
import random
import glob
import time
import sys # Importar sys para leer los argumentos de la línea de comandos

# =========================================================================
# === SCRIPT TRABAJADOR: MODIFICADO PARA SER PORTABLE (POTENCIADO) ===
# Este script es llamado por 'app_video.py'.
# Recibe la carpeta de entrada y salida como argumentos.
# =========================================================================


# --- CONFIGURACIÓN PRINCIPAL ---
# La ruta del proyecto ahora solo se usa para encontrar recursos locales
# como 'ruido.mp3', que debe estar en la misma carpeta que este script.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_random_value(base, tolerance):
    """Genera un valor flotante aleatorio dentro de un rango."""
    return base + random.uniform(-tolerance, tolerance)

def procesar_variaciones_multimedia(entrada_dir, salida_dir, crf=23, preset="medium", seed=None):
    """
    Aplica una pila de transformaciones potentes y dinámicas.
    Recibe las carpetas de entrada y salida como parámetros.
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

    # --- Búsqueda de archivos multimedia ---
    print(f"\nBuscando archivos multimedia en: {entrada_dir}")
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
        base_name = long_base_name.split('__')[0]

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
            
            vf_chain = f"setsar=1,{geo['vf']},{color['vf']}"
            if ruido_vid["vf"]:
                vf_chain += f",{ruido_vid['vf']}"

            vf_chain += ",crop=floor(iw/2)*2:floor(ih/2)*2,scale=w='max(iw,720)':h=-2"
            recipe_name = f"{geo['name']}_{color['name']}_{ruido_vid['name']}_{audio_recipe['name']}"
            dst_path = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp4")

            if os.path.exists(ruido_path) and aplicar_ruido:
                af_chain_complex = f"[0:a]{af_chain},volume=1.0[main];[1:a]volume={get_random_value(0.015, 0.005)},aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first[a]"
                recipe_name += "_con_ruido"
                dst_path = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp4")
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path, "-i", ruido_path,
                    "-filter_complex", f"[0:v]{vf_chain},format=yuv420p[v];{af_chain_complex}",
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-map_metadata", "-1", dst_path
                ]
            else:
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-vf", vf_chain, "-af", af_chain,
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-map_metadata", "-1", dst_path
                ]
        
        elif extension == ".mp3":
            dst_path = os.path.join(salida_dir, f"{base_name}__{audio_recipe['name']}.mp3")
            cmd_base = [ffmpeg_cmd, "-y", "-i", src_path]

            if os.path.exists(ruido_path) and aplicar_ruido:
                af_chain_complex = f"[0:a]{af_chain},volume=1.0[main];[1:a]volume={get_random_value(0.015, 0.005)},aloop=loop=-1:size=2e+09[noise];[main][noise]amix=inputs=2:duration=first[a]"
                dst_path = os.path.join(salida_dir, f"{base_name}__{audio_recipe['name']}_con_ruido.mp3")
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
            raise e
        except Exception as e:
            print(f"Error inesperado: {e}")
            raise e

    print(f"\nProceso completado. Archivos guardados en: {salida_dir}")

# --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python ai_studio_code_potenciado_video.py <ruta_carpeta_entrada> <ruta_carpeta_salida>")
        sys.exit(1)

    entrada_dir_arg = sys.argv[1]
    salida_dir_arg = sys.argv[2]
    
    print("==============================================")
    print("=== INICIO DEL SCRIPT TRABAJADOR (POTENCIADO) ===")
    print("==============================================")
    
    procesar_variaciones_multimedia(entrada_dir_arg, salida_dir_arg, crf=24, preset="fast")
    
    print("\n==============================================")
    print("=== SCRIPT TRABAJADOR (POTENCIADO) FINALIZADO ===")
    print("==============================================")