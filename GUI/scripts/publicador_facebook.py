import requests
import os
import time

def publicar_video(video_path, descripcion, page_id, access_token):
    """
    Sube un video como un REEL a una Fan Page de Facebook,
    replicando el proceso de 4 pasos validado manualmente con curl.
    """
    if not os.path.exists(video_path):
        return f"❌ Error de Archivo: El video no se encuentra en la ruta: {video_path}"

    try:
        # --- PASO 1: Iniciar la Sesión de Subida ---
        # Replica tu curl #1, que funcionó.
        init_url = f"https://graph.facebook.com/v23.0/{page_id}/video_reels"
        print("   -> PASO 1/4: Iniciando sesión de subida de Reel...")
        
        init_payload = {
            'upload_phase': 'start',
            'access_token': access_token,
        }
        init_response = requests.post(init_url, data=init_payload, timeout=60).json()

        if 'video_id' not in init_response:
            print(f"      [DEBUG] Respuesta de Facebook en Paso 1: {init_response}")
            return f"❌ Error de API (Paso 1): {init_response.get('error', {}).get('message', 'La respuesta no contenía video_id.')}"

        video_id = init_response['video_id']
        upload_url = init_response['upload_url']

        # --- PASO 2: Subir el Archivo de Video ---
        # Replica tu curl #2, que funcionó.
        print(f"   -> PASO 2/4: Subiendo el archivo de video (ID: {video_id})...")
        
        headers = {
            'Authorization': f'OAuth {access_token}',
            'offset': '0',
            'file_size': str(os.path.getsize(video_path))
        }
        
        with open(video_path, 'rb') as video_file:
            video_data = video_file.read()

        transfer_response = requests.post(upload_url, headers=headers, data=video_data, timeout=900).json()

        if not transfer_response.get('success'):
            print(f"      [DEBUG] Respuesta de Facebook en Paso 2: {transfer_response}")
            return f"❌ Error de API (Paso 2): {transfer_response.get('error', {}).get('message', 'La subida del archivo falló.')}"

        # --- PASO 3: Publicar el Reel ---
        # Replica tu curl #3, que funcionó.
        print("   -> PASO 3/4: Solicitando la publicación del Reel...")
        
        finish_payload = {
            'video_id': video_id,
            'upload_phase': 'finish',
            'video_state': 'PUBLISHED',
            'description': descripcion,
            'access_token': access_token,
        }
        
        finish_response = requests.post(init_url, data=finish_payload, timeout=120).json()
        
        if not finish_response.get('success'):
            print(f"      [DEBUG] Respuesta de Facebook en Paso 3: {finish_response}")
            return f"❌ Error de API (Paso 3): {finish_response.get('error', {}).get('message', 'La solicitud de publicación falló.')}"
        
        # --- PASO 4: Verificar el Estado Final ---
        # Replica tu curl #4, que funcionó.
        print(f"   -> PASO 4/4: Verificando estado final de la publicación...")
        status_url = f"https://graph.facebook.com/v23.0/{video_id}"
        status_params = {'fields': 'status', 'access_token': access_token}

        for attempt in range(15): # Esperamos un máximo de 7.5 minutos
            status_response = requests.get(status_url, params=status_params, timeout=60).json()
            video_status = status_response.get('status', {}).get('video_status')

            if video_status == 'ready':
                return f"✅ ¡REEL publicado y verificado con éxito! ID del Video: {video_id}"
            
            print(f"      - Estado actual: '{video_status}'. Esperando 30s... (Intento {attempt + 1}/15)")
            time.sleep(30)
        
        return f"⚠️ Advertencia: El Reel fue enviado a publicar, pero no se pudo confirmar el estado 'ready' a tiempo. ID: {video_id}"

    except requests.exceptions.RequestException as e:
        return f"❌ Error de Red: No se pudo conectar con los servidores de Facebook. ({e})"
    except Exception as e:
        return f"❌ Ocurrió un error inesperado durante la publicación del Reel: {e}"