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
    ffmpeg_cmd = None
    print("\nBuscando FFmpeg local dentro del entorno virtual...")
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_cmd):
            print(f"FFmpeg encontrado en: {ffmpeg_cmd}")
        else:
            ffmpeg_cmd = None
    except Exception as e:
        print(f"Error al localizar FFmpeg: {e}")

    if not ffmpeg_cmd:
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

    # ===== EFECTOS AGRESIVOS - SOLO SE APLICAN 1 VEZ =====
    # Opciones: 'blur_fondo' o 'grano_agresivo'
    MODO = "grano_agresivo"  # <<< CAMBIA AQUI: 'blur_fondo' o 'grano_agresivo'

    recetas_audio = [
        {"name": "reverb_sutil", "af": "aecho=0.8:0.88:40:0.25"},
        {"name": "pitch_up",     "af": "asetrate=44100*1.02,atempo=0.9804,aresample=44100"},
    ]

    for i, src_path in enumerate(media_files):
        long_base_name = os.path.splitext(os.path.basename(src_path))[0]
        base_name = long_base_name.split('_')[0]
        # Preservar banderas criticas en el nombre
        if "blur_fondo"    in long_base_name: base_name += "_blur_fondo"
        if "grano_agresivo" in long_base_name: base_name += "_grano_agresivo"

        extension = os.path.splitext(src_path)[1].lower()
        print(f"\nProcesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        # Si ya se aplico el efecto estructural, no lo repetimos
        ya_aplicado = ("blur_fondo" in long_base_name or "grano_agresivo" in long_base_name)

        audio_recipe = random.choice(recetas_audio)

        if extension == ".mp4":
            ya_aplicado = ("hyper_tiktok" in long_base_name)
            dst_path = os.path.join(salida_dir, f"{base_name}_hyper_tiktok_{audio_recipe['name']}.mp4")

            if ya_aplicado:
                # Ya tiene los efectos estructurales, solo audio
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-vf", "null",
                    "-af", audio_recipe['af'],
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", dst_path
                ]
                print(f"    Ya tiene estructura, solo audio.")
            else:
                # Aplica HYPER TIKTOK: 65/35 achatado, fondo plasma y flashes
                fc_parts = []
                # 1. Fondo Plasma infinito (720x1280)
                fc_parts.append("mandelbrot=size=720x1280:rate=30,format=yuv420p,eq=saturation=0.1:brightness=-0.4[bg];")
                # 2. Video original escalado a 720x832 (65% achatado)
                fc_parts.append("[0:v]scale=720:832,setsar=1[fg];")
                # 3. Mezclar video sobre el fondo. shortest=1 corta cuando termina el video original.
                fc_parts.append("[bg][fg]overlay=x=0:y=0:shortest=1[split_screen];")
                
                # 4. Generar 75 flashes distribuidos (cubre hasta 5 mins de video sin ffprobe)
                overlay_filters = "[split_screen]"
                for j in range(75):
                    t_start = (j * 4.0) + random.uniform(0.5, 3.0)
                    t_end = t_start + random.uniform(0.3, 0.8)
                    x = random.randint(50, 500)
                    y = random.randint(100, 700)
                    color = random.choice(["red@0.7", "blue@0.7", "yellow@0.7", "green@0.7", "magenta@0.7", "cyan@0.7"])
                    
                    overlay_filters += f"drawbox=x={x}:y={y}:w={random.randint(100,300)}:h={random.randint(100,300)}:color={color}:t=fill:enable='between(t,{t_start:.1f},{t_end:.1f})'"
                    
                    if j < 74:
                        overlay_filters += ","
                overlay_filters += "[out]"
                fc_parts.append(overlay_filters)
                filter_complex = "".join(fc_parts)
                
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-filter_complex", filter_complex,
                    "-map", "[out]", "-map", "0:a?",
                    "-af", audio_recipe['af'],
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", dst_path
                ]
                print(f"    Aplicando: hyper_tiktok + audio")
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
                    print(f"    Archivo generado: {os.path.basename(dst_path)}")
                except subprocess.CalledProcessError as e:
                    print(f"    Error de FFmpeg: {e.stderr.decode('utf-8', errors='ignore')[-500:]}")
                except Exception as ex:
                    print(f"    Error inesperado: {ex}")

        elif extension == ".mp3":
            dst_path = os.path.join(salida_dir, f"{base_name}_{audio_recipe['name']}.mp3")
            cmd = [ffmpeg_cmd, "-y", "-i", src_path, "-af", audio_recipe['af'], "-c:a", "libmp3lame", "-b:a", "192k", dst_path]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
                print(f"    Archivo generado: {os.path.basename(dst_path)}")
            except Exception as ex:
                print(f"    Error: {ex}")

    print(f"\nProceso completado. Archivos guardados en: {salida_dir}")


if __name__ == "__main__":
    print("==============================================")
    print(">>> ENTRO A AI_STUDIO_CODE_AGRESIVO (Filtro 65/35) <<<")
    print("==============================================")

    import sys
    in_dir  = sys.argv[1] if len(sys.argv) > 1 else None
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None

    procesar_variaciones_multimedia(crf=23, preset="medium", entrada_dir=in_dir, salida_dir=out_dir)

    print("\n==============================================")
    print("=== SCRIPT FINALIZADO ===")
    print("==============================================")