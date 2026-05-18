import requests

# La URL de tu API de LLM.
API_URL = "http://localhost:5004/chat"

def generar_texto_video(nombre_video, instrucciones_ia):
    payload = {"mensaje": instrucciones_ia}
    
    try:
        print(f"[DEBUG] Enviando payload a {API_URL}")
        response = requests.post(API_URL, json=payload, timeout=300)
        response.raise_for_status()
        
        contenido_llm = response.json()
        descripcion_generada = contenido_llm['choices'][0]['message']['content']
        
        print(f"[DEBUG] Respuesta completa de la IA:")
        print(f"'{descripcion_generada}'")
        print(f"[DEBUG] Longitud de la respuesta: {len(descripcion_generada)} caracteres")
        
        # Parsear la respuesta
        titulo = "Video Viral"  # valor por defecto
        descripcion = descripcion_generada.strip()
        
        # Buscar el título
        if "**Título:**" in descripcion_generada:
            titulo_match = descripcion_generada.split("**Título:**")[1].split("\n")[0].strip()
            if titulo_match:
                titulo = titulo_match
                print(f"[DEBUG] Título extraído: '{titulo}'")
        
        # Buscar la descripción
        if "**Descripción:**" in descripcion_generada:
            descripcion_match = descripcion_generada.split("**Descripción:**")[1].strip()
            if descripcion_match:
                descripcion = descripcion_match
                print(f"[DEBUG] Descripción extraída: '{descripcion}'")
                print(f"[DEBUG] Longitud de descripción: {len(descripcion)} caracteres")

        datos_finales = {
            "titulo": titulo,
            "descripcion": descripcion
        }
        
        print(f"[DEBUG] Datos finales:")
        print(f"  Título: '{datos_finales['titulo']}'")
        print(f"  Descripción completa: '{datos_finales['descripcion']}'")
        
        return datos_finales

    except requests.exceptions.RequestException as e:
        return {"error": f"Error de conexión con tu API Flask en {API_URL}. Detalles: {e}"}
    except Exception as e:
        respuesta_bruta = response.text if 'response' in locals() else "Sin respuesta del servidor."
        return {"error": f"No se pudo procesar la respuesta de la IA. Error: {e}. Respuesta recibida: {respuesta_bruta[:200]}"}