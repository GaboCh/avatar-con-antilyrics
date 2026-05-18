import os
import time
import random
import requests
import json
import sys
import subprocess
import glob
import shutil
from pathlib import Path

# Importamos nuestros nuevos módulos v2
import descargador_instagram_v2
import publicador_tiktok_v2

# Endpoint de FaceSwap (usando el servicio original en el puerto 5100)
SWAP_ENDPOINT = 'http://127.0.0.1:5100/swap'
# Endpoint de Groq (nuestro nuevo servicio en el puerto 5005)
GROQ_ENDPOINT = 'http://127.0.0.1:5005/chat'

def flujo_completo_tiktok(ig_user, max_videos, face_model, tiktok_session, prompt_base, modo_prueba, anticopy_cycles, log_func):
    """
    Orquesta el flujo: Instagram -> FaceSwap -> Anti-Copyright -> Groq -> TikTok
    """
    log_func(f"🚀 INICIANDO AUTOMATIZACIÓN TIKTOK PARA @{ig_user}")
    log_func("="*60)

    # 1. DESCARGAR
    videos_descargados = descargador_instagram_v2.descargar_videos_usuario(ig_user, max_videos, log_func=log_func)
    
    if not videos_descargados:
        log_func("❌ No se pudieron descargar videos. Abortando flujo.")
        return

    # 2. PROCESAR CADA VIDEO
    for i, video_path in enumerate(videos_descargados, 1):
        log_func(f"\n🎬 PROCESANDO VIDEO {i}/{len(videos_descargados)}: {os.path.basename(video_path)}")
        
        # --- PASO A: Face Swap ---
        log_func(f"   🎭 Realizando Face Swap con modelo: {face_model}")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gui_dir = os.path.dirname(script_dir)
        face_path = os.path.join(gui_dir, 'proyectos_gui', 'swap', 'modelos', face_model, 'face.jpeg')

        if not os.path.exists(face_path):
            log_func(f"   ❌ Error: No se encontró la cara del modelo en {face_path}")
            continue

        video_swap_path = None
        try:
            with open(face_path, 'rb') as f_img, open(video_path, 'rb') as v_file:
                files = {'face': f_img, 'video': v_file}
                resp = requests.post(SWAP_ENDPOINT, files=files, timeout=600)
            
            if resp.status_code == 200:
                finales_dir = os.path.join(gui_dir, 'proyectos_gui', 'swap', 'videos_finales')
                os.makedirs(finales_dir, exist_ok=True)
                video_swap_path = os.path.join(finales_dir, f"swap_{os.path.basename(video_path)}")
                with open(video_swap_path, 'wb') as f:
                    f.write(resp.content)
                log_func(f"   ✅ Face Swap completado.")
            else:
                log_func(f"   ❌ Error en el servicio de Swap: {resp.status_code}")
                continue
        except Exception as e:
            log_func(f"   ❌ Error de conexión con FaceFusion: {e}")
            continue

        # --- PASO B: Post-Procesamiento (FFmpeg) ---
        # Este paso es vital y me lo había saltado. Equivale a tu Pestaña 4.
        log_func("   ✨ Aplicando Post-Procesamiento (FFmpeg Re-encode)...")
        procesados_dir = os.path.join(gui_dir, 'proyectos_gui', 'swap', 'videos_finales_procesados')
        os.makedirs(procesados_dir, exist_ok=True)
        video_procesado_path = os.path.join(procesados_dir, f"proc_{os.path.basename(video_swap_path)}")
        
        try:
            # Comando FFmpeg idéntico al de tu pestaña 4
            cmd_ffmpeg = [
                'ffmpeg', '-i', video_swap_path,
                '-c:v', 'libx264', '-crf', '21', '-preset', 'medium',
                '-c:a', 'copy', '-y', video_procesado_path
            ]
            subprocess.run(cmd_ffmpeg, capture_output=True, text=True, check=True)
            log_func("      ✅ Re-codificación completada.")
        except Exception as e:
            log_func(f"      ⚠️ Falló FFmpeg: {e}. Se intentará seguir con el archivo swap.")
            video_procesado_path = video_swap_path

        # --- PASO C: Anti-Copyright ---
        log_func("   🛡️ Aplicando proceso Anti-Copyright...")
        video_anticopy_path = None
        try:
            anticopy_script = os.path.join(gui_dir, 'anticopryng', 'app_video.py')
            work_dir = os.path.join(gui_dir, 'anticopryng', 'temp_work_v2')
            w_in = os.path.join(work_dir, 'videos_finales')
            w_out = os.path.join(work_dir, 'videos_finales_procesados')
            
            if os.path.exists(work_dir): shutil.rmtree(work_dir)
            os.makedirs(w_in); os.makedirs(w_out)
            
            # Copiamos el video RE-CODIFICADO al taller de Anti-Copyright
            shutil.copy(video_procesado_path, w_in)
            log_func("   -> Video procesado copiado a la carpeta temporal. Iniciando script...")
            
            # Ejecutamos el script y leemos su salida línea por línea
            cmd = [sys.executable, anticopy_script, w_in, w_out, str(int(anticopy_cycles))]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            
            for line in proc.stdout:
                if line.strip():
                    log_func(f"      [AntiCopy] {line.strip()}")
            proc.wait()
            
            # En la Pestaña original (auto_swap_gui.py), app_video.py deja el resultado FINAL de nuevo en w_in (work_input_dir)
            archivos_res = glob.glob(os.path.join(w_in, "*.mp4"))
            if archivos_res:
                # Tomamos el primer archivo como en el original
                resultado_final_path = archivos_res[0]
                video_anticopy_path = os.path.join(gui_dir, 'anticopryng', 'videos_anticopyright', f"ready_{os.path.basename(video_swap_path)}")
                os.makedirs(os.path.dirname(video_anticopy_path), exist_ok=True)
                shutil.move(resultado_final_path, video_anticopy_path)
                log_func("   ✅ Proceso Anti-Copyright completado y movido a salida final.")
            else:
                log_func("   ❌ ¡ERROR CRÍTICO! No se encontró el archivo final en el taller de Anti-Copyright.")
                video_anticopy_path = video_swap_path
        except Exception as e:
            log_func(f"   ⚠️ Error crítico en Anti-Copyright (excepción): {e}. Usando video sin aplicar este proceso.")
            video_anticopy_path = video_swap_path

        # --- PASO C: Generar Texto con Groq ---
        log_func("   🧠 Generando título y descripción con Groq...")
        try:
            payload = {"mensaje": f"{prompt_base}\nVideo: {os.path.basename(video_path)}"}
            resp_groq = requests.post(GROQ_ENDPOINT, json=payload, timeout=30)
            
            if resp_groq.status_code == 200:
                full_text = resp_groq.json()['choices'][0]['message']['content']
                descripcion = full_text.strip()
                log_func(f"   ✅ Texto generado con éxito.")
            else:
                descripcion = f"Video by @{ig_user} #viral #reels"
                log_func(f"   ⚠️ Error en Groq ({resp_groq.status_code}), usando descripción por defecto.")
        except Exception as e:
            descripcion = f"Video by @{ig_user} #viral #reels"
            log_func(f"   ⚠️ Fallo conexión con Groq, usando descripción por defecto.")

        # --- PASO D: Subir a TikTok ---
        log_func("   📤 Subiendo a TikTok...")
        # Usamos el video procesado por Anti-Copyright
        resultado = publicador_tiktok_v2.publicar_video_tiktok(video_anticopy_path, descripcion, session_id=tiktok_session, log_func=log_func)
        log_func(f"   {resultado}")

        # --- PASO E: Espera de 10 a 20 minutos (O 2 min en modo prueba) ---
        if i < len(videos_descargados):
            if modo_prueba:
                espera_segundos = 120 # 2 minutos para pruebas
                log_func(f"   🧪 MODO PRUEBA ACTIVO: Esperando solo 2 minutos...")
            else:
                espera_segundos = random.randint(600, 1200) # 10-20 minutos
                log_func(f"   ⏳ Esperando {espera_segundos // 60} minutos antes del siguiente video...")
            
            time.sleep(espera_segundos)

    log_func(f"\n{'='*60}\n🎯 AUTOMATIZACIÓN COMPLETADA")
