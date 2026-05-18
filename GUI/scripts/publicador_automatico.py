import os
import time
import random 

# Se asume que estos archivos están en la misma carpeta.
# Si dan error de importación, es porque no existen o tienen otro nombre.
try:
    import generador_texto_llm
    import publicador_facebook
except ImportError as e:
    # Este es un error crítico. Si ocurre, necesitamos saberlo.
    print(f"ERROR CRÍTICO: No se pudo importar un módulo necesario: {e}")
    # Creamos funciones falsas para que el programa no se caiga al intentar llamarlas.
    class FakeModule:
        def generar_texto_video(self, *args, **kwargs):
            return {"error": f"El archivo 'generador_texto_llm.py' no se encuentra o tiene un error."}
        def publicar_video(self, *args, **kwargs):
            return f"❌ Error: El archivo 'publicador_facebook.py' no se encuentra o tiene un error."
    generador_texto_llm = FakeModule()
    publicador_facebook = FakeModule()


# --- COMIENZA LA FUNCIÓN CORREGIDA ---

def procesar_y_publicar_lote(videos_seleccionados, prompt_ia, log_func, gui_dir, fb_page_id, fb_access_token):
    """
    Función orquestadora principal. Procesa una lista de videos y los publica.
    Esta es la única función que el GUI necesitará llamar.
    
    Args:
        videos_seleccionados (list): Lista de nombres de archivo de video.
        prompt_ia (str): Instrucciones para la IA.
        log_func (function): La función print de la consola de Gradio.
        gui_dir (str): La ruta base del directorio GUI para construir rutas de archivo.
        fb_page_id (str): El ID de la página de Facebook.
        fb_access_token (str): El token de acceso a la página de Facebook.
    """
    log_func("🚀 Iniciando Proceso de Publicación Automática...")
    log_func(f"Instrucciones para la IA: \"{prompt_ia}\"")
    log_func("="*60)

    exitosos = 0
    fallidos = 0

    # enumerate(..., 1) hace que el contador 'i' empiece en 1 en lugar de 0
    for i, nombre_video in enumerate(videos_seleccionados, 1):
        log_func(f"\n🔄 Procesando video {i}/{len(videos_seleccionados)}: {nombre_video}")
        
        # --- PASO 1: Generar texto con la IA ---
        log_func(f"   1. 🧠 Generando texto con IA...")
        texto_generado = generador_texto_llm.generar_texto_video(nombre_video, prompt_ia)

        if "error" in texto_generado:
            log_func(f"      ❌ ERROR al generar texto: {texto_generado['error']}")
            log_func(f"   Saltando la publicación de este video.")
            fallidos += 1
            continue
            
        titulo = texto_generado.get('titulo', 'Título no generado por la IA')
        descripcion = texto_generado.get('descripcion', 'Descripción no generada por la IA.')
        log_func(f"      - Título (solo para log): {titulo}")
        log_func(f"      - Descripción: {descripcion[:80]}...") 

        # --- PASO 2: Publicar en Facebook ---
        log_func(f"   2. 🌐 Publicando en Facebook...")
        video_path = os.path.join(gui_dir, 'anticopryng', 'videos_anticopyright', nombre_video)
        
        resultado_publicacion = publicador_facebook.publicar_video(
            video_path,
            descripcion, 
            fb_page_id, 
            fb_access_token
        )
        
        log_func(f"   -> {resultado_publicacion}")

        if "✅" in resultado_publicacion:
            exitosos += 1
        else:
            fallidos += 1
        
        # --- LÓGICA DE PAUSA CORREGIDA ---
        # Verificamos si NO es el último video para aplicar una pausa.
        if i < len(videos_seleccionados):
            
            # Para el PRIMER video, la pausa corta se mantiene igual.
            if i == 1:
                pausa_corta_segundos = 15 
                log_func(f"   ✅ Primer video procesado. Esperando {pausa_corta_segundos} segundos antes de iniciar las pausas largas...")
                time.sleep(pausa_corta_segundos)
            
            # Para el RESTO de videos, aquí va la cuenta regresiva.
            else:
                tiempos_de_espera_minutos = [10, 20, 40, 60]
                pausa_en_minutos = random.choice(tiempos_de_espera_minutos)
                log_func(f"   ⏳ Iniciando pausa aleatoria de {pausa_en_minutos} minutos...")
                
                # LA CUENTA REGRESIVA ESTÁ AHORA DENTRO DEL 'ELSE'
                for minuto_restante in range(pausa_en_minutos, 0, -1):
                    log_func(f"      💤 Tiempo restante: {minuto_restante} minuto(s)...")
                    time.sleep(60) # Espera 1 minuto
                
                # ESTE MENSAJE SE MUESTRA UNA SOLA VEZ AL FINAL DE LA PAUSA
                log_func(f"   ⏰ ¡Pausa finalizada! Continuando con el siguiente video...")

    # --- MENSAJE FINAL, AHORA FUERA DEL BUCLE PRINCIPAL ---
    log_func(f"\n{'*'*60}\n*** PUBLICACIÓN AUTOMÁTICA COMPLETADA ***")
    log_func(f"✅ Publicados con éxito: {exitosos}")
    log_func(f"❌ Publicaciones fallidas: {fallidos}")
    log_func(f"{'*'*60}")

# --- FIN DE LA FUNCIÓN CORREGIDA ---```
