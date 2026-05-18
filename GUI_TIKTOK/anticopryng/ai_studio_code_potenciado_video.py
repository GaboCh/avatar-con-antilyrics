import os
import subprocess
import random
import glob
import time
import sys

# =========================================================================
# === SCRIPT TRABAJADOR: ANTI-COPYRIGHT POTENCIADO (v2 - INVISIBLE) ===
# Segunda pasada — aplica un conjunto diferente de transformaciones para
# acumular cambios en el fingerprint sin que sean visibles.
# Puede mezclar ruido.mp3 de fondo (volumen ultra-bajo).
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


def get_rval(base, tol):
    return base + random.uniform(-tol, tol)


def procesar_variaciones_multimedia(entrada_dir, salida_dir, crf=23, preset="fast", seed=None):
    """
    Segunda pasada de transformaciones imperceptibles.
    Usa un banco distinto al script normal para maximizar la variación del
    fingerprint acumulado. El ruido de fondo (ruido.mp3) se mezcla a un
    volumen inaudible (~1.5%) para alterar el hash de audio sin que se
    escuche ningún ruido.

    Sincronía audio-video garantizada:
      - Filtros de video puro no tocan el audio.
      - Filtros de audio puro no tocan el video.
      - Tempo: mismo factor numérico en atempo y setpts.
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

    print(f"Procesando {len(media_files)} archivos (pasada potenciada)...")

    ruido_path  = os.path.join(PROJECT_DIR, "ruido.mp3")
    tiene_ruido = os.path.exists(ruido_path)

    # =====================================================================
    # BANCOS DE TRANSFORMACIONES — segunda pasada, diferente al script normal
    # =====================================================================

    def receta_geo_potenciada():
        """
        Crop asimétrico agresivo + zoom combinado: desplaza la composición
        varios píxeles desde bordes aleatorios.
        """
        cx = random.randint(3, 7)
        cy = random.randint(3, 7)
        lado_x = random.choice([0, cx])   # cortar desde izquierda o derecha
        lado_y = random.choice([0, cy])
        zoom   = round(random.uniform(1.003, 1.007), 4)
        opciones = [
            {"name": "crop_zoom",    "vf": f"scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}"},
            {"name": "crop_offset",  "vf": f"crop=iw-{cx}:ih-{cy}:{lado_x}:{lado_y},scale=iw+{cx}:ih+{cy}"},
            {"name": "rot_zoom",     "vf": f"rotate={random.uniform(-0.003,0.003):.4f}:ow=iw:oh=ih:c=none,scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}"},
        ]
        return random.choice(opciones)

    def receta_color_potenciada():
        """
        Combinación de ajustes de color: hue + gamma + color balance simultáneos.
        Cada uno es imperceptible; juntos acumulan más cambio de fingerprint.
        """
        hue = round(random.uniform(-3.0, 3.0), 3)
        gam = round(random.uniform(0.982, 1.018), 4)
        sat = round(random.uniform(0.988, 1.012), 4)
        rs  = round(random.uniform(-0.010, 0.010), 4)
        gs  = round(random.uniform(-0.005, 0.005), 4)
        bs  = round(random.uniform(-0.010, 0.010), 4)
        opciones = [
            # Hue + saturación
            {"name": "hue_sat",    "vf": f"hue=h={hue}:s={sat}"},
            # Gamma + colorbalance combinados
            {"name": "gamma_bal",  "vf": f"eq=gamma={gam}:saturation={sat},colorbalance=rs={rs}:gs={gs}:bs={bs}"},
            # Solo colorbalance más pronunciado
            {"name": "color_push", "vf": f"colorbalance=rs={rs}:gs={gs}:bs={bs}"},
            # Contraste + hue
            {"name": "cont_hue",   "vf": f"eq=contrast={round(random.uniform(0.996,1.004),4)}:brightness={round(random.uniform(-0.004,0.004),4)},hue=h={hue}"},
        ]
        return random.choice(opciones)

    def receta_audio_potenciada():
        """
        Segunda pasada de audio con técnicas complementarias al script normal.
        El ruido.mp3 se mezcla a volumen ~1.5% (inaudible) si está disponible.

        Reglas de sync:
          - pitch_*: asetrate + atempo compensatorio → duración idéntica → safe
          - tempo_sutil: mismo factor en atempo y setpts → safe
          - dynaudnorm / aecho / equalizer: no cambian duración → safe
        """
        r_up   = round(random.uniform(1.012, 1.028), 4)
        r_down = round(random.uniform(0.972, 0.988), 4)
        t_val  = round(random.uniform(0.985, 1.015), 4)
        freq   = random.randint(80, 8000)
        gain   = random.choice([1, 2])
        delay1 = random.randint(8, 16)
        delay2 = random.randint(20, 35)
        ev1    = round(random.uniform(0.002, 0.004), 4)
        ev2    = round(random.uniform(0.001, 0.003), 4)
        mlev   = round(random.uniform(0.975, 1.025), 4)

        opciones = [
            {"name": "pitch_up2",     "af": f"asetrate=44100*{r_up},aresample=44100,atempo={round(1/r_up,4)}",   "vf_extra": ""},
            {"name": "pitch_down2",   "af": f"asetrate=44100*{r_down},aresample=44100,atempo={round(1/r_down,4)}","vf_extra": ""},
            {"name": "tempo2",        "af": f"atempo={t_val}",                                                     "vf_extra": f"setpts=PTS/{t_val}"},
            {"name": "dynorm",        "af": "dynaudnorm=f=200:g=5",                                               "vf_extra": ""},
            {"name": "eq_micro",      "af": f"equalizer=f={freq}:width_type=h:width=100:g={gain}",               "vf_extra": ""},
            {"name": "echo2",         "af": f"aecho=0.85:0.65:{delay1}:{ev1},{delay2}:{ev2}",                    "vf_extra": ""},
            {"name": "stereo2",       "af": f"stereotools=mlev={mlev}",                                           "vf_extra": ""},
        ]
        return random.choice(opciones)

    # =====================================================================
    # PROCESAMIENTO
    # =====================================================================
    for i, src_path in enumerate(media_files):
        base_name = os.path.splitext(os.path.basename(src_path))[0].split('__')[0]
        extension = os.path.splitext(src_path)[1].lower()
        print(f"\nProcesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        audio    = receta_audio_potenciada()
        af_chain = audio['af']
        vf_extra = audio.get('vf_extra', '')

        # Decidir si mezclar ruido.mp3 de fondo (2 de cada 3 veces)
        usar_ruido = tiene_ruido and random.choice([True, True, False])
        vol_ruido  = round(get_rval(0.015, 0.005), 4)   # ~1.5%, inaudible

        if extension == ".mp4":
            geo   = receta_geo_potenciada()
            color = receta_color_potenciada()

            partes_vf = []
            if vf_extra:
                partes_vf.append(vf_extra)
            partes_vf += ["setsar=1", geo['vf'], color['vf'],
                          "crop=floor(iw/2)*2:floor(ih/2)*2",
                          "scale=w='max(iw,720)':h=-2"]
            vf_chain    = ",".join(p for p in partes_vf if p)
            recipe_name = f"{geo['name']}_{color['name']}_{audio['name']}"

            if usar_ruido:
                recipe_name += "_ruido"
                dst_path = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp4")
                # Ruido mezclado: inaudible, no altera duración del audio principal
                af_complex = (
                    f"[0:a]{af_chain},volume=1.0[main];"
                    f"[1:a]volume={vol_ruido},aloop=loop=-1:size=2000000000[bg];"
                    f"[main][bg]amix=inputs=2:duration=first[a]"
                )
                vf_complex = f"[0:v]{vf_chain},format=yuv420p[v]"
                if encoder == "h264_nvenc":
                    cmd = [
                        ffmpeg_cmd, "-y", "-i", src_path, "-i", ruido_path,
                        "-filter_complex", f"{vf_complex};{af_complex}",
                        "-map", "[v]", "-map", "[a]",
                        "-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(crf),
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "-map_metadata", "-1", dst_path
                    ]
                else:
                    cmd = [
                        ffmpeg_cmd, "-y", "-i", src_path, "-i", ruido_path,
                        "-filter_complex", f"{vf_complex};{af_complex}",
                        "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "-map_metadata", "-1", dst_path
                    ]
            else:
                dst_path = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp4")
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
            if usar_ruido:
                recipe_name += "_ruido"
                dst_path    = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp3")
                af_complex  = (
                    f"[0:a]{af_chain},volume=1.0[main];"
                    f"[1:a]volume={vol_ruido},aloop=loop=-1:size=2000000000[bg];"
                    f"[main][bg]amix=inputs=2:duration=first[a]"
                )
                cmd = [
                    ffmpeg_cmd, "-y", "-i", src_path, "-i", ruido_path,
                    "-filter_complex", af_complex,
                    "-c:a", "libmp3lame", "-b:a", "192k",
                    "-map_metadata", "-1", dst_path
                ]
            else:
                dst_path = os.path.join(salida_dir, f"{base_name}__{recipe_name}.mp3")
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
        print("Uso: python ai_studio_code_potenciado_video.py <entrada> <salida>")
        sys.exit(1)
    print("=== SCRIPT TRABAJADOR (POTENCIADO v2) ===")
    procesar_variaciones_multimedia(sys.argv[1], sys.argv[2], crf=24, preset="fast")
    print("=== FINALIZADO ===")