import os
import glob
import subprocess
import time
import random
import sys
from pathlib import Path
import shutil
import gradio as gr
import configparser

# IMPORTAMOS LOS NUEVOS MÓDULOS V2
import orquestador_tiktok_v2

# =========== CONFIGURACIÓN DE RUTAS ===========
script_dir = os.path.abspath(os.path.dirname(__file__))
gui_dir = os.path.dirname(script_dir)
BASE_DIR = os.path.join(gui_dir, 'proyectos_gui')
SWAP_DIR = os.path.join(BASE_DIR, 'swap')
URL_FILE = os.path.join(SWAP_DIR, 'url', 'url.txt')

# --- CONSOLA VIRTUAL PARA GRADIO ---
class GradioConsole:
    def __init__(self):
        self.buffer = ""
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

    def write(self, text):
        self.buffer += text
        self.old_stdout.write(text)
        self.old_stdout.flush() 
        
    def flush(self):
        pass

    def get_buffer(self):
        return self.buffer
    
    def clear_buffer(self):
        self.buffer = ""

    def start_redirect(self):
        sys.stdout = self
        sys.stderr = self

    def stop_redirect(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

console = GradioConsole()

# --- FUNCIONES DE SOPORTE ---
def obtener_modelos_disponibles():
    modelos_dir = os.path.join(SWAP_DIR, 'modelos')
    if not os.path.exists(modelos_dir): return []
    modelos_validos = []
    for nombre_modelo in os.listdir(modelos_dir):
        ruta_modelo = os.path.join(modelos_dir, nombre_modelo)
        if os.path.isdir(ruta_modelo) and os.path.exists(os.path.join(ruta_modelo, 'face.jpeg')):
            modelos_validos.append(nombre_modelo)
    return sorted(modelos_validos)

def crear_estructura_carpetas():
    console.clear_buffer(); console.start_redirect()
    print("📂 Creando estructura de carpetas...")
    os.makedirs(BASE_DIR, exist_ok=True)
    carpetas_swap = [
        os.path.join(SWAP_DIR, 'modelos', 'alexa'),
        os.path.join(SWAP_DIR, 'videos_originales'),
        os.path.join(SWAP_DIR, 'videos_finales'),
        os.path.join(SWAP_DIR, 'videos_finales_procesados'),
        os.path.join(SWAP_DIR, 'url'),
        os.path.join(SWAP_DIR, 'cookies'),
    ]
    for carpeta in carpetas_swap: os.makedirs(carpeta, exist_ok=True)
    anticopyright_output_dir = os.path.join(gui_dir, 'anticopryng', 'videos_anticopyright')
    os.makedirs(anticopyright_output_dir, exist_ok=True)
    print("\n✅ Estructura de carpetas lista.")
    output = console.get_buffer(); console.stop_redirect(); return output

def get_url_content():
    if os.path.exists(URL_FILE):
        with open(URL_FILE, 'r', encoding='utf-8') as f: return f.read()
    return "# Pega aquí las URLs de Instagram"

def save_url_content(new_content):
    try:
        with open(URL_FILE, 'w', encoding='utf-8') as f: f.write(new_content)
        return "✅ Archivo url.txt guardado."
    except Exception as e: return f"❌ Error al guardar: {e}"

# --- FUNCIONES PARA COOKIES (ALINEADAS CON EL PROYECTO) ---
def get_cookies_ig():
    path = os.path.join(SWAP_DIR, 'cookies', 'www.instagram.com_cookies.txt')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return f.read()
    return "# Pega aquí tus cookies de Instagram (Netscape)"

def save_cookies_ig(content):
    path = os.path.join(SWAP_DIR, 'cookies', 'www.instagram.com_cookies.txt')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    return "✅ Cookies de Instagram guardadas en www.instagram.com_cookies.txt"

def get_cookies_tt():
    path = os.path.join(SWAP_DIR, 'cookies', 'www.tiktok.com_cookies.txt')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return f.read()
    return "# Pega aquí tus cookies de TikTok (Netscape)"

def save_cookies_tt(content):
    path = os.path.join(SWAP_DIR, 'cookies', 'www.tiktok.com_cookies.txt')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    return "✅ Cookies de TikTok guardadas en www.tiktok.com_cookies.txt"

# --- FUNCIÓN DE EJECUCIÓN ---
def ejecutar_auto_tiktok(ig_user, max_videos, face_models, prompt_base, modo_prueba, anticopy_cycles):
    console.clear_buffer(); console.start_redirect()
    if not ig_user:
        ig_user = "usuario_desconocido" # Ya no es obligatorio, es solo para logs y fallback
    if not face_models:
        print("❌ Error: Debes seleccionar al menos un modelo de cara.")
        output = console.get_buffer(); console.stop_redirect(); return output

    face_model_chosen = random.choice(face_models)
    
    orquestador_tiktok_v2.flujo_completo_tiktok(
        ig_user=ig_user,
        max_videos=max_videos,
        face_model=face_model_chosen,
        tiktok_session=None,
        prompt_base=prompt_base,
        modo_prueba=modo_prueba,
        anticopy_cycles=anticopy_cycles,
        log_func=print
    )
    output = console.get_buffer(); console.stop_redirect(); return output

# =========== INTERFAZ DE GRADIO ===========
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Auto-Downloader & TikTok Automation V2")
    output_console = gr.Textbox(label="📄 Consola de Salida", lines=12, autoscroll=True, interactive=False)

    with gr.Tabs():
        with gr.TabItem("1. Configuración y URLs"):
            btn_crear_carpetas = gr.Button("📁 Crear Estructura de Carpetas", variant="secondary")
            url_editor = gr.Textbox(value=get_url_content, label="📝 Contenido de url.txt", lines=10)
            btn_save_urls = gr.Button("💾 Guardar url.txt", variant="primary")
                
        with gr.TabItem("7. 🚀 Auto-TikTok (Instagram)"):
            gr.Markdown("### Automatización (Descarga url.txt -> FaceSwap -> AntiCopy -> TikTok)")
            
            with gr.Accordion("📝 Lista de URLs (url.txt)", open=True):
                gr.Markdown("Pega aquí los enlaces de los Reels que quieres procesar (uno por línea):")
                url_editor_t7 = gr.Textbox(value=get_url_content, label="", lines=5)
                btn_save_urls_t7 = gr.Button("💾 Guardar URLs", variant="secondary")

            with gr.Accordion("🍪 Gestión de Cookies (IG/TT)", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Cookies Instagram")
                        cook_ig = gr.Textbox(value=get_cookies_ig, lines=5, label="www.instagram.com_cookies.txt")
                        btn_save_ig = gr.Button("💾 Guardar Instagram", variant="secondary")
                    with gr.Column():
                        gr.Markdown("#### Cookies TikTok")
                        cook_tt = gr.Textbox(value=get_cookies_tt, lines=5, label="www.tiktok.com_cookies.txt")
                        btn_save_tt = gr.Button("💾 Guardar TikTok", variant="secondary")

            with gr.Row():
                with gr.Column():
                    ig_user_input = gr.Textbox(label="👤 Etiqueta de Usuario (opcional, para texto)", placeholder="ej: lindavargasofi")
                    max_videos_input = gr.Slider(1, 15, value=3, step=1, label="📥 Máx. URLs a procesar")
                with gr.Column():
                    modelos_disponibles = obtener_modelos_disponibles()
                    checkbox_modelos_tiktok = gr.CheckboxGroup(choices=modelos_disponibles, label="🎭 Caras", value=modelos_disponibles[:1])
                    cb_modo_prueba = gr.Checkbox(label="🧪 Modo Prueba (2 min espera)", value=False)
                    anticopy_cycles_slider = gr.Slider(1, 10, value=1, step=1, label="🛡️ Ciclos Anticopy")
            
            prompt_groq_input = gr.Textbox(label="🧠 Prompt IA", lines=3, value="Crea un título corto y una descripción de máximo 20 palabras con 3 hashtags virales.")
            btn_run_tiktok = gr.Button("🔥 INICIAR PROCESO AUTOMÁTICO", variant="primary")

    # LOGICA
    btn_crear_carpetas.click(fn=crear_estructura_carpetas, outputs=output_console)
    btn_save_urls.click(fn=save_url_content, inputs=url_editor, outputs=output_console)
    btn_save_urls_t7.click(fn=save_url_content, inputs=url_editor_t7, outputs=output_console)
    btn_save_ig.click(fn=save_cookies_ig, inputs=cook_ig, outputs=output_console)
    btn_save_tt.click(fn=save_cookies_tt, inputs=cook_tt, outputs=output_console)
    btn_run_tiktok.click(fn=ejecutar_auto_tiktok, inputs=[ig_user_input, max_videos_input, checkbox_modelos_tiktok, prompt_groq_input, cb_modo_prueba, anticopy_cycles_slider], outputs=output_console)

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
