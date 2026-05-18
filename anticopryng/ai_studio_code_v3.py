# app.py

import os
import subprocess
import random
import glob
import time

# =========================================================================
# === INSTRUCCIONES DE USO (VERSIÓN 3 - TRIPLE CAPA) ===
# 1. Guarda este archivo como 'app.py' en tu carpeta de proyecto.
# 2. Abre una terminal en esa misma carpeta y activa tu entorno virtual.
# 3. **CRÍTICO:** Asegúrate de tener el archivo 'ruido.mp3' en la carpeta.
#    Ahora es una parte fundamental de la "Capa 3: Engaño Perceptual".
# 4. Coloca tus archivos MP4 y MP3 en la carpeta 'videos_finales'.
# 5. Ejecuta el script: python app.py
# =========================================================================


# --- CONFIGURACIÓN PRINCIPAL ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_random_value(base, tolerance):
    return base + random.uniform(-tolerance, tolerance)

def procesar_variaciones_multimedia(crf=24, preset="fast", seed=None):
    """
    Aplica una pila de 3 capas de ofuscación a cada archivo para un
    nivel máximo de evasión contra sistemas de IA avanzados.
    """
    if seed is None:
        random.seed(time.time())
    else:
        random.seed(seed)

    entrada_dir = os.path.join(PROJECT_DIR, "videos_finales") 
    salida_dir = os.path.join(PROJECT_DIR, "videos_finales_procesados")
    
    print(f"📁 Asegurando que las carpetas existan en: {PROJECT_DIR}")
    os.makedirs(entrada_dir, exist_ok=True)
    os.makedirs(salida_dir, exist_ok=True)
    print(f"✅ Carpetas creadas/verificadas: '{os.path.basename(entrada_dir)}', '{os.path.basename(salida_dir)}'")

    # --- Lógica de búsqueda de FFmpeg (robusta) ---
    ffmpeg_cmd = "ffmpeg"
    try:
        subprocess.run([ffmpeg_cmd, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ FFmpeg encontrado en el PATH del sistema.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("🟡 FFmpeg no encontrado en el PATH. Buscando con imageio-ffmpeg...")
        try:
            import imageio_ffmpeg
            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"✅ FFmpeg encontrado en: {ffmpeg_cmd}")
        except Exception:
            print("\n❌ ERROR FATAL: No se pudo encontrar FFmpeg. Asegúrate de que esté en el PATH o instala 'imageio-ffmpeg'.")
            return
        
    media_files = sorted(glob.glob(os.path.join(entrada_dir, "*.mp4"))) + \
                  sorted(glob.glob(os.path.join(entrada_dir, "*.mp3")))

    if not media_files:
        print(f"⚠️ No se encontraron archivos en '{entrada_dir}'.")
        return

    print(f"🎬 Iniciando postprocesamiento de {len(media_files)} archivos multimedia...")

    recetas_capa1 = [
        {"name": "pitch_up", "af": f"asetrate=44100*{get_random_value(1.03, 0.015)},aresample=44100"},
        {"name": "pitch_down", "af": f"asetrate=44100*{get_random_value(0.97, 0.015)},aresample=44100"},
        {"name": "tempo_var", "af": f"atempo={get_random_value(1.0, 0.04)}"},
        {"name": "combo_ligero", "af": f"atempo={get_random_value(1.02, 0.01)},asetrate=44100*{get_random_value(1.01, 0.01)},aresample=44100"},
    ]

    # Recetas de video (sin cambios)
    recetas_video = [f"rotate={get_random_value(0, 0.01)}", f"scale=iw*{get_random_value(1.01, 0.005)}:ih*{get_random_value(1.01, 0.005)},crop=iw/{get_random_value(1.01, 0.005)}:ih/{get_random_value(1.01, 0.005)}", "hflip", f"eq=contrast={get_random_value(1.01, 0.01)}", f"eq=saturation={get_random_value(1.05, 0.02)}", "noise=alls=1:allf=t+u", "gblur=sigma=0.1"]

    for i, src_path in enumerate(media_files):
        base_name = os.path.splitext(os.path.basename(src_path))[0]
        extension = os.path.splitext(src_path)[1].lower()
        
        print(f"\n🔄 Procesando {i+1}/{len(media_files)}: {os.path.basename(src_path)}")

        # ======================= INICIO DE LA CORRECCIÓN MÁS ESTRICTA =======================
        
        # 1. Entrada de audio: Asegura el formato y divide en dos flujos explícitamente
        #    La cadena comienza con la entrada [0:a] y la etiqueta como [input_audio]
        #    Luego divide [input_audio] en [main_audio_stream] y [ghost_audio_stream]
        audio_input_chain = "[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates=44100[input_audio];" + \
                            "[input_audio]asplit=2[main_audio_stream][ghost_audio_stream];"

        # 2. Capa 1: Aplica la receta seleccionada al flujo principal
        capa1_recipe = random.choice(recetas_capa1)
        capa1_chain = f"[main_audio_stream]{capa1_recipe['af']}[L1_out];"

        # 3. Capa 2: Deformación Estructural, encadenada a [L1_out]
        capa2_chain = ("[L1_out]asplit=3[l][m][h];" +
                       "[l]lowpass=f=250[bass];" +
                       "[m]bandpass=f=1000:width_type=h:w=1500[mids];" +
                       "[h]highpass=f=4000[treble];" +
                       f"[bass]atempo={get_random_value(0.99, 0.005)}[b_mod];" +
                       f"[mids]vibrato=f={get_random_value(0.5, 0.2)}:d=0.1[m_mod];" +
                       f"[treble]aphaser=speed={get_random_value(0.3, 0.1)}:decay=0.1[t_mod];" +
                       "[b_mod][m_mod][t_mod]amix=inputs=3[L2_out];") # Note el ; al final

        # 4. Capa 3: Engaño Perceptual, mezclando [L2_out] con la pista fantasma y ruido (si existe)
        ruido_path = os.path.join(PROJECT_DIR, "ruido.mp3")
        
        if os.path.exists(ruido_path):
            capa3_chain = (f"[ghost_audio_stream]areverse,volume=0.03[ghost];" +
                           f"[1:a]volume={get_random_value(0.025, 0.01)},aloop=loop=-1:size=2e+09[noise];" +
                           "[L2_out][ghost][noise]amix=inputs=3:duration=first[final_audio_pre_norm];")
            inputs_needed = [ruido_path]
        else:
            # Aquí no hay ruido.mp3, solo se mezcla la pista principal procesada con la fantasma invertida.
            capa3_chain = (f"[ghost_audio_stream]areverse,volume=0.04[ghost];" +
                           "[L2_out][ghost]amix=inputs=2:duration=first[final_audio_pre_norm];")
            inputs_needed = []

        # 5. Normalización final y salida del audio procesado, encadenado a [final_audio_pre_norm]
        final_normalization_chain = "[final_audio_pre_norm]loudnorm=I=-16:TP=-1.5:LRA=11:print_format=summary[a_out]"

        # Construye la cadena de filtros de audio completa
        full_audio_filter_complex = audio_input_chain + capa1_chain + capa2_chain + capa3_chain + final_normalization_chain
        
        # ======================== FIN DE LA CORRECCIÓN MÁS ESTRICTA =========================
        
        recipe_name = f"cerbero_{capa1_recipe['name']}"
        dst_path = os.path.join(salida_dir, f"{base_name}_{recipe_name}.{extension[1:]}")

        cmd = [ffmpeg_cmd, "-y", "-i", src_path]
        for extra_input in inputs_needed:
            cmd.extend(["-i", extra_input])

        if extension == ".mp4":
            vf_chain = "setsar=1," + ",".join(random.sample(recetas_video, 4))
            # La cadena de filtros de video y audio se combinan
            final_filter = f"[0:v]{vf_chain}[v];{full_audio_filter_complex}"
            cmd.extend([
                "-filter_complex", final_filter,
                "-map", "[v]", "-map", "[a_out]",
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-map_metadata", "-1", dst_path
            ])
        elif extension == ".mp3":
            cmd.extend([
                "-filter_complex", full_audio_filter_complex,
                "-map", "[a_out]",
                "-c:a", "libmp3lame", "-b:a", "192k", "-map_metadata", "-1", dst_path
            ])
        else:
            continue

        try:
            print(f"    Aplicando receta 'Cerbero' de Triple Capa: [{recipe_name}]")
            process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"✅ Archivo generado: {os.path.basename(dst_path)}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error de FFmpeg procesando {os.path.basename(src_path)}")
            print(f"   Comando ejecutado: {' '.join(cmd)}")
            print(f"   Mensaje de FFmpeg STDOUT: {e.stdout.decode(errors='ignore')}")
            print(f"   Mensaje de FFmpeg STDERR: {e.stderr.decode(errors='ignore')}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")

    print(f"\n🎯 Proceso completado. Archivos guardados en: {salida_dir}")


if __name__ == "__main__":
    print("==============================================")
    print("=== SCRIPT ANTI-COPYRIGHT v3 (CERBERO ACÚSTICO) ===")
    print("==============================================")
    
    procesar_variaciones_multimedia()