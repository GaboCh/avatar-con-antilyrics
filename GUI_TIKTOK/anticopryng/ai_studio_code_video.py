import os
import subprocess
import random
import glob
import time

# --- CONFIGURACION PRINCIPAL ---
PROJECT_DIR = os.path.dirname(__file__)

def procesar_variaciones_multimedia(crf=21, preset="medium", seed=None, entrada_dir=None, salida_dir=None):
    if seed is None:
        random.seed(time.time())
    else:
        random.seed(seed)

    if not entrada_dir:
        entrada_dir = os.path.join(PROJECT_DIR, "videos_finales")
    if not salida_dir:
        salida_dir = os.path.join(PROJECT_DIR, "videos_finales_procesados")

    print(f"Asegurando que las carpetas existan en: {PROJECT_DIR}")
    os.makedirs(entrada_dir, exist_ok=True)
    os.makedirs(salida_dir, exist_ok=True)
    print(f"Carpetas creadas/verificadas: '{os.path.basename(entrada_dir)}', '{os.path.basename(salida_dir)}'")

    # --- Busqueda de FFmpeg ---
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
            print(f"No se encontro ffprobe.exe junto a ffmpeg")
    except ImportError:
        print("Error: La libreria 'imageio-ffmpeg' no esta instalada.")
    except Exception as e:
        print(f"Error al localizar FFmpeg: {e}")

    if not ffmpeg_cmd or not ffprobe_cmd:
        print("\nERROR FATAL: No se pudo encontrar FFmpeg. El script no puede continuar.")
        return

    # --- Busqueda de archivos multimedia ---
    print(f"\nBuscando archivos .mp4 y .mp3 en: {entrada_dir}")
    media_files = sorted(glob.glob(os.path.join(entrada_dir, "*.mp4"))) + \
                  sorted(glob.glob(os.path.join(entrada_dir, "*.mp3")))

    if not media_files:
        print(f"No se encontraron archivos en '{entrada_dir}'.")
        return

    print(f"Iniciando postprocesamiento de {len(media_files)} archivos multimedia...")

    # ===== BANCOS DE TRANSFORMACIONES (SIN ESPEJO - SEGURO PARA TEXTO) =====
    recetas_geometricas = [
        {"name": "crop_leve", "vf": "scale=iw*1.05:ih*1.05,crop=iw/1.05:ih/1.05"},
        {"name": "zoom_leve", "vf": "scale=iw*1.02:ih*1.02,crop=iw/1.02:ih/1.02"},
    ]
    recetas_color = [
        {"name": "luciernaga",      "vf": "FILTER_COMPLEX"},  # Luciernaga brillante - SIEMPRE PRIMERO
        {"name": "premium_calido",  "vf": "colorbalance=rm=0.03:bm=-0.03,vignette=angle=0.1,noise=alls=5:allf=t+u,unsharp=5:5:0.5:5:5:0.0"},
        {"name": "premium_frio",    "vf": "colorbalance=bm=0.03:rm=-0.03,vignette=angle=0.1,noise=alls=5:allf=t+u,unsharp=5:5:0.5:5:5:0.0"},
        {"name": "premium_kodak",   "vf": "colorbalance=rs=0.04:gs=0.02:bs=-0.02,vignette=angle=0.12,noise=alls=4:allf=t+u,unsharp=5:5:0.5:5:5:0.0"},
    ]

    # Audio sincronizado: asetrate compensado con atempo para no desincronizar video
    recetas_audio_mejoradas = [
        {"name": "pitch_up",    "af": "asetrate=44100*1.03,atempo=0.97087,aresample=44100"},
        {"name": "pitch_down",  "af": "asetrate=44100*0.97,atempo=1.03093,aresample=44100"},
        {"name": "reverb_sala", "af": "aecho=0.8:0.88:40:0.25"},
        {"name": "chorus_suave","af": "chorus=0.5:0.9:50:0.4:0.25:2"},
        {"name": "bass_boost",  "af": "equalizer=f=60:width_type=h:width=20:g=3"},
    ]

    # ===== PROCESAMIENTO =====
    for i, src_path in enumerate(media_files):
        long_base_name = os.path.splitext(os.path.basename(src_path))[0]
        base_name = long_base_name.split('_')[0]
        if "blur_marco"  in long_base_name: base_name += "_blur_marco"
        if "blur_fondo"  in long_base_name: base_name += "_blur_fondo"
        if "marco_grueso" in long_base_name: base_name += "_marco_grueso"

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
            geo   = random.choice(recetas_geometricas)
            color = recetas_color[0]  # Luciernaga siempre (para probar - cambiar a random.choice despues)
            recipe_name = f"{geo['name']}_{color['name']}_{audio_recipe['name']}"
            dst_path = os.path.join(salida_dir, f"{base_name}_{recipe_name}.mp4")

            if color['name'] == 'luciernaga':
                # Efecto Copos/Luciernagas usando RGB (El elegido por el usuario)
                expr = "min(255, 255 * lt(mod(X + 6*sin(Y/40.0+T/2.0), 55), 3) * lt(mod(Y + T*35, 80), 3))"
                fc = (
                    f"[0:v]{geo['vf']},format=rgb24,split=2[orig][blank];"
                    f"[blank]geq=r='{expr}':g='{expr}':b='{expr}'[copos_raw];"
                    "[copos_raw]boxblur=2:1[copos];"
                    "[orig][copos]blend=all_mode=screen:all_opacity=0.75,"
                    "format=yuv420p,crop=floor(iw/2)*2:floor(ih/2)*2[out]"
                )
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-filter_complex", fc,
                    "-map", "[out]", "-map", "0:a",
                    "-af", af_chain,
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", dst_path
                ]
            else:
                vf_chain = f"setsar=1,{geo['vf']},{color['vf']},crop=floor(iw/2)*2:floor(ih/2)*2,scale=w='max(iw,720)':h=-2"
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
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           stdin=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
            print(f"Archivo generado: {os.path.basename(dst_path)}")
        except KeyboardInterrupt:
            print(f"    [AVISO] Senal de interrupcion ignorada.")
            print(f"Archivo generado: {os.path.basename(dst_path)}")
        except subprocess.CalledProcessError:
            print(f"Error de FFmpeg procesando {os.path.basename(src_path)}")
        except Exception as e:
            print(f"Error inesperado: {e}")

    print(f"\nProceso completado. Archivos guardados en: {salida_dir}")


# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    print("==============================================")
    print("=== INICIO DEL SCRIPT DE PROCESAMIENTO MULTIMEDIA ===")
    print("==============================================")

    import sys
    in_dir  = sys.argv[1] if len(sys.argv) > 1 else None
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None

    procesar_variaciones_multimedia(crf=23, preset="medium", entrada_dir=in_dir, salida_dir=out_dir)

    print("\n==============================================")
    print("=== SCRIPT FINALIZADO ===")
    print("==============================================")