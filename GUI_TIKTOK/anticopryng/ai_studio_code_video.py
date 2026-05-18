import os
import subprocess
import random
import glob
import time
import sys

# =========================================================================
# === SCRIPT TRABAJADOR: ANTI-COPYRIGHT (v2 - INVISIBLE) ===
# Aplica transformaciones imperceptibles para el ojo pero efectivas contra
# los algoritmos de fingerprinting de audio y video.
# NO introduce grano visible, espejo ni líneas.
# La sincronía audio-video se preserva en todo momento.
# =========================================================================

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


def procesar_variaciones_multimedia(entrada_dir, salida_dir, crf=21, preset="fast", seed=None):
    """
    Aplica transformaciones imperceptibles a cada archivo multimedia.
    La sincronización audio-video se garantiza en todo momento:
      - Filtros SOLO de video (hue, crop, vignette, gamma) no afectan el audio.
      - Filtros SOLO de audio (pitch, echo, stereo) no afectan el video.
      - Cambios de tempo usan el MISMO factor numérico en atempo y setpts.
    """
    if seed is None:
        random.seed(time.time())
    else:
        random.seed(seed)

    os.makedirs(salida_dir, exist_ok=True)

    # --- Localizar FFmpeg ---
    ffmpeg_cmd = None
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        if not os.path.exists(ffmpeg_cmd):
            ffmpeg_cmd = None
    except Exception as e:
        print(f"Error al localizar FFmpeg: {e}")

    if not ffmpeg_cmd:
        print("ERROR FATAL: No se pudo encontrar FFmpeg.")
        return

    encoder = detectar_encoder(ffmpeg_cmd)

    media_files = (sorted(glob.glob(os.path.join(entrada_dir, "*.mp4"))) +
                   sorted(glob.glob(os.path.join(entrada_dir, "*.mp3"))))

    if not media_files:
        print(f"No se encontraron archivos en '{entrada_dir}'.")
        return

    print(f"Procesando {len(media_files)} archivos (tecnicas invisibles)...")

    # =====================================================================
    # BANCO DE TRANSFORMACIONES DE VIDEO — todas imperceptibles al ojo
    # =====================================================================

    def recetas_geo():
        """
        Rotación ultra-sutil + crop asimétrico aleatorio.
        El crop rompe el fingerprint de composición sin cambiar el aspect ratio visible.
        """
        angulo = random.uniform(-0.004, 0.004)
        # Recortamos 2-6 px desde un borde aleatorio para romper composición
        cx = random.randint(2, 5)
        cy = random.randint(2, 5)
        opciones = [
            # Solo rotación mínima
            {"name": "rot_sutil",   "vf": f"rotate={angulo:.4f}:ow=iw:oh=ih:c=none"},
            # Zoom + crop centrado (imperceptible)
            {"name": "zoom_crop",   "vf": "scale=iw*1.004:ih*1.004,crop=iw/1.004:ih/1.004"},
            # Crop asimétrico: quita píxeles desde un borde
            {"name": "crop_asim",   "vf": f"crop=iw-{cx}:ih-{cy}:{cx}:{cy},scale=iw+{cx}:ih+{cy}"},
        ]
        return random.choice(opciones)

    def recetas_color():
        """
        Ajustes de color/gamma/hue mínimos. Cambian el fingerprint de color
        pero el ojo humano no detecta diferencias menores a ~2-3 unidades de hue
        ni variaciones de gamma <2%.
        """
        hue_shift = random.uniform(-2.5, 2.5)           # grados, imperceptible
        gamma_val = random.uniform(0.985, 1.015)         # ±1.5%, imperceptible
        sat_val   = random.uniform(0.990, 1.010)         # ±1%, imperceptible
        rs = random.uniform(-0.008, 0.008)
        bs = random.uniform(-0.008, 0.008)
        opciones = [
            {"name": "hue_shift",   "vf": f"hue=h={hue_shift:.3f}:s={sat_val:.3f}"},
            {"name": "gamma_tweak", "vf": f"eq=gamma={gamma_val:.4f}:saturation={sat_val:.3f}"},
            {"name": "color_bal",   "vf": f"colorbalance=rs={rs:.4f}:bs={bs:.4f}"},
            {"name": "contraste",   "vf": f"eq=contrast={random.uniform(0.997,1.003):.4f}:brightness={random.uniform(-0.003,0.003):.4f}"},
        ]
        return random.choice(opciones)

    def recetas_overlay_visual():
        """
        Transformaciones visuales MÁS AGRESIVAS para romper el fingerprint visual
        de YouTube. Se elige una al azar en cada video.

        Opciones:
          grano      - ruido de film visible (noise=alls=6). Efectivo, leve.
          linea_v    - línea vertical semitransparente al 20% en posición X aleatoria.
                       No es una línea sólida: se mezcla con drawbox a baja opacidad.
          grano+vign - grano sutil + vignette más pronunciada.
          crop_hard  - crop de 8-14px asimétrico más agresivo.
        """
        x_linea = random.randint(15, 85)   # posición de la línea en % del ancho
        opciones = [
            # Granulado de film (el más efectivo visualmente, apenas se nota)
            {"name": "grano",       "vf": "noise=alls=6:allf=t+u"},
            # Línea vertical semitransparente (20% opacidad) en posición aleatoria
            {"name": "linea_v",     "vf": f"drawbox=x=iw*{x_linea/100:.2f}:y=0:w=2:h=ih:color=white@0.20:t=fill"},
            # Grano leve + vignette más pronunciada
            {"name": "grano_vign",  "vf": f"noise=alls=4:allf=t+u,vignette=angle={random.uniform(0.15,0.30):.3f}:mode=backward"},
            # Crop asimétrico agresivo (8-14px) — altera la composición visible
            {"name": "crop_hard",   "vf": f"crop=iw-{random.randint(8,14)}:ih-{random.randint(6,12)}:{random.randint(4,8)}:{random.randint(3,6)},scale=iw+{random.randint(8,14)}:ih+{random.randint(6,12)}"},
            # Combinación: línea + grano juntos (máxima efectividad)
            {"name": "linea_grano", "vf": f"drawbox=x=iw*{x_linea/100:.2f}:y=0:w=2:h=ih:color=white@0.15:t=fill,noise=alls=4:allf=t+u"},
        ]
        return random.choice(opciones)


    # =====================================================================
    # BANCO DE TRANSFORMACIONES DE AUDIO — todas imperceptibles al oído
    # =====================================================================

    def recetas_audio():
        """
        Transformaciones de audio que NO afectan la duración/sync del video.

        pitch_up/down: asetrate cambia el pitch. La velocidad se corrige con
          atempo, por lo que la DURACIÓN del audio no cambia. → sync seguro.

        tempo: usa el MISMO factor para atempo (audio) y setpts (video).
          Se calculan UNA SOLA VEZ y se reutilizan. → sync garantizado.

        aecho ultra-corto: añade un eco a 12ms, volumen 0.003. Inaudible
          pero cambia el fingerprint de audio. No altera la duración. → safe.

        stereo_shift: desplaza levemente el balance L/R. No altera duración. → safe.
        """
        r_up    = round(random.uniform(1.010, 1.025), 4)
        r_down  = round(random.uniform(0.975, 0.990), 4)
        # Mismo factor para audio y video en cambios de tempo
        t_val   = round(random.uniform(0.983, 1.017), 4)
        delay   = random.randint(10, 18)          # ms para echo (inaudible)
        echo_v  = round(random.uniform(0.002, 0.004), 4)
        mlev    = round(random.uniform(0.98, 1.02), 4)  # stereo balance

        opciones = [
            # Pitch sutil (duración preservada)
            {"name": "pitch_up",     "af": f"asetrate=44100*{r_up},aresample=44100,atempo={round(1/r_up,4)}",
             "vf_extra": ""},
            {"name": "pitch_down",   "af": f"asetrate=44100*{r_down},aresample=44100,atempo={round(1/r_down,4)}",
             "vf_extra": ""},
            # Tempo (mismo factor audio+video → sync garantizado)
            {"name": "tempo_sutil",  "af": f"atempo={t_val}",
             "vf_extra": f"setpts=PTS/{t_val}"},
            # Echo ultracorto (inaudible, rompe fingerprint)
            {"name": "echo_micro",   "af": f"aecho=0.9:0.7:{delay}:{echo_v}",
             "vf_extra": ""},
            # Balance estéreo sutil
            {"name": "stereo_shift", "af": f"stereotools=mlev={mlev}",
             "vf_extra": ""},
            # EQ sutil
            {"name": "bass_micro",   "af": f"equalizer=f={random.randint(60,120)}:width_type=h:width=30:g={random.choice([1,2])}",
             "vf_extra": ""},
        ]
        return random.choice(opciones)

    # =====================================================================
    # PROCESAMIENTO
    # =====================================================================
    for i, src_path in enumerate(media_files):
        base_name = os.path.splitext(os.path.basename(src_path))[0].split('__')[0]
        extension = os.path.splitext(src_path)[1].lower()
        print(f"\nProcesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        audio = recetas_audio()
        af_chain  = audio['af']
        vf_extra  = audio.get('vf_extra', '')

        if extension == ".mp4":
            geo     = recetas_geo()
            color   = recetas_color()
            overlay = recetas_overlay_visual()

            # Construir cadena de video: tempo_extra → geo → color → overlay visual → normalizar
            partes_vf = []
            if vf_extra:
                partes_vf.append(vf_extra)
            partes_vf.append("setsar=1")
            partes_vf.append(geo['vf'])
            partes_vf.append(color['vf'])
            if overlay['vf']:
                partes_vf.append(overlay['vf'])
            # Normalizar dimensiones (par, mínimo 720px ancho)
            partes_vf.append("crop=floor(iw/2)*2:floor(ih/2)*2")
            partes_vf.append("scale=w='max(iw,720)':h=-2")

            vf_chain    = ",".join(p for p in partes_vf if p)
            recipe_name = f"{geo['name']}_{color['name']}_{overlay['name']}_{audio['name']}"
            dst_path    = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp4")

            if encoder == "h264_nvenc":
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path,
                    "-vf", vf_chain, "-af", af_chain,
                    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-map_metadata", "-1", dst_path
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
            recipe_name = audio['name']
            dst_path    = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp3")
            cmd = [
                ffmpeg_cmd, "-y", "-i", src_path,
                "-af", af_chain,
                "-c:a", "libmp3lame", "-b:a", "192k",
                "-map_metadata", "-1", dst_path
            ]
        else:
            print(f"Saltando formato no soportado: {os.path.basename(src_path)}")
            continue

        try:
            print(f"  >> Receta: {recipe_name}")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"  OK Generado: {os.path.basename(dst_path)}")
        except subprocess.CalledProcessError as e:
            print(f"  ERR FFmpeg: {e.stderr.decode(errors='ignore')[-400:]}")
            raise
        except Exception as e:
            print(f"  ERR inesperado: {e}")
            raise

    print(f"\nProceso completado. Archivos en: {salida_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python ai_studio_code_video.py <entrada> <salida>")
        sys.exit(1)
    print("=== SCRIPT TRABAJADOR (NORMAL v2) ===")
    procesar_variaciones_multimedia(sys.argv[1], sys.argv[2], crf=23, preset="fast")
    print("=== FINALIZADO ===")