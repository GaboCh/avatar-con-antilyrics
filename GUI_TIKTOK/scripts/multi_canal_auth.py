"""
multi_canal_auth.py
Gestiona la autenticacion de multiples canales de YouTube.
Cada canal tiene su propia carpeta con su token.pickle.
Usa subidor_youtube.autenticar_youtube() sin modificarlo.
"""
import os
import sys
import shutil

script_dir      = os.path.abspath(os.path.dirname(__file__))
gui_tiktok_dir  = os.path.dirname(script_dir)
BASE_DIR        = os.path.join(gui_tiktok_dir, 'proyectos_tiktok')
CREDENCIALES_DIR = os.path.join(BASE_DIR, 'credenciales_youtube')
CANALES_DIR     = os.path.join(CREDENCIALES_DIR, 'canales')
CLIENT_SECRETS  = os.path.join(CREDENCIALES_DIR, 'client_secrets.json')


def _canal_dir(nombre):
    return os.path.join(CANALES_DIR, nombre)


def listar_canales():
    """Retorna lista de nombres de canales que tienen carpeta creada."""
    if not os.path.exists(CANALES_DIR):
        return []
    return sorted([
        d for d in os.listdir(CANALES_DIR)
        if os.path.isdir(os.path.join(CANALES_DIR, d))
    ])


def canal_autenticado(nombre):
    """Retorna True si el canal ya tiene token guardado."""
    token = os.path.join(_canal_dir(nombre), 'token.pickle')
    return os.path.exists(token)


def _guardar_nombre_real(canal_dir, youtube):
    """Consulta el nombre real del canal en YouTube y lo guarda en nombre_canal.txt."""
    try:
        resp  = youtube.channels().list(part='snippet', mine=True).execute()
        items = resp.get('items', [])
        if items:
            nombre_real = items[0]['snippet']['title']
            with open(os.path.join(canal_dir, 'nombre_canal.txt'), 'w', encoding='utf-8') as f:
                f.write(nombre_real)
    except Exception:
        pass


def leer_nombre_real(nombre):
    """Retorna el nombre real del canal de YouTube guardado, o None si no existe."""
    txt = os.path.join(_canal_dir(nombre), 'nombre_canal.txt')
    if os.path.exists(txt):
        with open(txt, encoding='utf-8') as f:
            return f.read().strip()
    return None


def autenticar_canal(nombre):
    """
    Abre el navegador para autenticar un canal de YouTube.
    Guarda el token en credenciales_youtube/canales/{nombre}/token.pickle
    Reutiliza client_secrets.json del directorio principal.
    """
    if not nombre or not nombre.strip():
        return "❌ Ingresa un nombre para el canal."

    nombre = nombre.strip().replace(' ', '_')

    if not os.path.exists(CLIENT_SECRETS):
        return (f"❌ No se encontro client_secrets.json en:\n   {CREDENCIALES_DIR}\n"
                "   Configura tus credenciales primero en la Pestana 1.")

    canal_dir = _canal_dir(nombre)
    os.makedirs(canal_dir, exist_ok=True)

    canal_secrets = os.path.join(canal_dir, 'client_secrets.json')
    if not os.path.exists(canal_secrets):
        shutil.copy(CLIENT_SECRETS, canal_secrets)

    sys.path.insert(0, script_dir)
    import subidor_youtube

    youtube = subidor_youtube.autenticar_youtube(canal_dir)
    if youtube:
        _guardar_nombre_real(canal_dir, youtube)
        nombre_real = leer_nombre_real(nombre)
        display     = f"'{nombre_real}'" if nombre_real else f"'{nombre}'"
        return f"✅ Canal {display} autenticado correctamente.\n   Token guardado en: canales/{nombre}/token.pickle"
    return f"❌ No se pudo autenticar el canal '{nombre}'."


def obtener_youtube_canal(nombre):
    """
    Retorna el objeto youtube autenticado para un canal.
    Retorna None si el canal no existe o falla la autenticacion.
    """
    canal_dir = _canal_dir(nombre)
    if not os.path.exists(canal_dir):
        return None
    sys.path.insert(0, script_dir)
    import subidor_youtube
    try:
        return subidor_youtube.autenticar_youtube(canal_dir)
    except Exception:
        return None


def eliminar_canal(nombre):
    """Elimina la carpeta del canal y su token."""
    if not nombre or not nombre.strip():
        return "❌ Selecciona un canal."
    canal_dir = _canal_dir(nombre.strip())
    if os.path.exists(canal_dir):
        shutil.rmtree(canal_dir)
        return f"✅ Canal '{nombre}' eliminado."
    return f"⚠️ Canal '{nombre}' no encontrado."


def estado_canales():
    """Retorna un resumen de texto con el estado de todos los canales."""
    canales = listar_canales()
    if not canales:
        return "No hay canales registrados aun."
    lineas = []
    for c in canales:
        estado = "✅ Autenticado" if canal_autenticado(c) else "⚠️ Sin token"
        lineas.append(f"  {estado} — {c}")
    return "Canales registrados:\n" + "\n".join(lineas)
