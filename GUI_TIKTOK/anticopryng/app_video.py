import os
import subprocess
import sys
import shutil
import time

# --- SCRIPT PORTABLE - NO HAY RUTAS FIJAS ---
# Este script es el "Gerente" del proceso. Es llamado por la UI de Gradio.
# Recibe las carpetas de trabajo temporales como argumentos y gestiona
# la ejecución de los scripts "trabajadores".

# --- FUNCIONES AUXILIARES ---

def preparar_entorno(base_proyecto, carpeta_entrada, carpeta_salida):
    """Asegura que las rutas y directorios de trabajo existan."""
    print("--- Preparando Entorno de Trabajo para el Subproceso ---")
    if not os.path.isdir(base_proyecto):
        print(f"ERROR: El directorio base de los scripts no existe: {base_proyecto}")
        sys.exit(1)
    
    print(f"Directorio base de scripts encontrado: {base_proyecto}")
    
    # Estas carpetas ya deberían haber sido creadas por el script principal (GUI)
    os.makedirs(carpeta_entrada, exist_ok=True)
    os.makedirs(carpeta_salida, exist_ok=True)
    print(f"Directorios de trabajo listos: '{os.path.basename(carpeta_entrada)}' y '{os.path.basename(carpeta_salida)}'")

def obtener_archivo_de_trabajo_inicial(carpeta_entrada):
    """
    Localiza y devuelve la ruta del único archivo en la carpeta de entrada temporal.
    """
    try:
        archivos = os.listdir(carpeta_entrada)
        if len(archivos) != 1:
            print(f"ERROR: Se esperaba 1 solo archivo en la carpeta de trabajo '{carpeta_entrada}', pero se encontraron {len(archivos)}.")
            sys.exit(1)
        
        ruta_completa_archivo = os.path.join(carpeta_entrada, archivos[0])
        print(f"Archivo inicial para procesar: {ruta_completa_archivo}")
        return ruta_completa_archivo
    except FileNotFoundError:
        print(f"ERROR: El directorio de entrada de trabajo '{carpeta_entrada}' no fue encontrado.")
        sys.exit(1)

def mover_y_actualizar(archivo_original_procesado, carpeta_entrada, carpeta_salida):
    """
    Mueve el resultado de la salida a la entrada y elimina el archivo original procesado.
    """
    try:
        archivos_salida = os.listdir(carpeta_salida)
        if not archivos_salida:
            print(f"ERROR: El script trabajador no generó ningún archivo en '{carpeta_salida}'.")
            sys.exit(1)

        # Mover el nuevo archivo (resultado) a la carpeta de entrada para el siguiente paso
        nombre_archivo_nuevo = archivos_salida[0]
        ruta_origen_nuevo = os.path.join(carpeta_salida, nombre_archivo_nuevo)
        ruta_destino_nuevo = os.path.join(carpeta_entrada, nombre_archivo_nuevo)

        print(f"   [ACCIÓN] Borrando archivo antiguo: {archivo_original_procesado}")
        os.remove(archivo_original_procesado)
        
        print(f"   [ACCIÓN] Moviendo '{ruta_origen_nuevo}' a '{ruta_destino_nuevo}'")
        shutil.move(ruta_origen_nuevo, ruta_destino_nuevo)
        
        # Limpiar la carpeta de salida para el próximo trabajador
        for f in os.listdir(carpeta_salida):
            os.remove(os.path.join(carpeta_salida, f))
            
        return ruta_destino_nuevo

    except Exception as e:
        print(f"ERROR durante el movimiento de archivos: {e}")
        sys.exit(1)


# --- FLUJO DE TRABAJO PRINCIPAL ---

def convertir_a_vertical(archivo_path, carpeta_entrada):
    """
    Convierte un video a formato vertical 9:16 (1080x1920) con fondo difuminado.
    Reemplaza el archivo original en la carpeta de entrada.
    """
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print(f"   [SHORTS] No se pudo obtener FFmpeg: {e}")
        return archivo_path

    nombre_base = os.path.splitext(os.path.basename(archivo_path))[0]
    extension   = os.path.splitext(archivo_path)[1]
    dst_path    = os.path.join(carpeta_entrada, nombre_base + "__vertical" + extension)

    filtro = (
        "[0:v]split=2[fg][bg_src];"
        "[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=luma_radius=40:luma_power=3[bg];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg_sc];"
        "[bg][fg_sc]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )

    cmd = [
        ffmpeg_cmd, "-y", "-i", archivo_path,
        "-filter_complex", filtro,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy", "-map_metadata", "-1", dst_path
    ]

    try:
        resultado = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        os.remove(archivo_path)
        print(f"   [SHORTS] Convertido a vertical 9:16: {os.path.basename(dst_path)}")
        return dst_path
    except subprocess.CalledProcessError as e:
        print(f"   [SHORTS] Error al convertir a vertical: {e.stderr[:300]}")
        return archivo_path


def main(carpeta_entrada, carpeta_salida, numero_de_ciclos, es_shorts=False):
    """
    Función principal que orquesta el flujo de trabajo.
    """
    # El directorio base es donde se encuentra este mismo script
    base_del_proyecto = os.path.dirname(os.path.abspath(__file__))
    
    scripts_trabajador = [
        "ai_studio_code_video.py",
        "ai_studio_code_potenciado_video.py",
    ]

    preparar_entorno(base_del_proyecto, carpeta_entrada, carpeta_salida)

    archivo_actual = obtener_archivo_de_trabajo_inicial(carpeta_entrada)

    if es_shorts:
        print("\n Modo Shorts: convirtiendo a vertical 9:16 con fondo difuminado...")
        archivo_actual = convertir_a_vertical(archivo_actual, carpeta_entrada)

    # Bucle Externo: Repite el proceso N veces
    for i in range(numero_de_ciclos):
        print(f"\n{'='*60}\n=== INICIANDO CICLO {i + 1}/{numero_de_ciclos} ===\n{'='*60}")

        # Bucle Interno: Ejecuta cada script trabajador en orden
        for nombre_script in scripts_trabajador:
            ruta_script_completa = os.path.join(base_del_proyecto, nombre_script)
            
            if not os.path.exists(ruta_script_completa):
                print(f"\nERROR: El script trabajador '{nombre_script}' no se encuentra en {ruta_script_completa}")
                sys.exit(1)

            print(f"\n--> Paso: Ejecutando '{nombre_script}'...")
            
            # Pasamos las carpetas de entrada y salida al script trabajador
            comando = [sys.executable, ruta_script_completa, carpeta_entrada, carpeta_salida]
            
            try:
                # Ejecuta el subproceso
                resultado = subprocess.run(
                    comando, check=True, capture_output=True, text=True,
                    encoding='utf-8', errors='ignore'
                )
                
                print(f"'{nombre_script}' finalizó exitosamente.")
                if resultado.stdout and resultado.stdout.strip():
                    print("   Salida del script trabajador:")
                    for linea in resultado.stdout.strip().splitlines():
                        print(f"     | {linea}")

                print("\n   Actualizando archivo de trabajo para el siguiente paso...")
                archivo_actual = mover_y_actualizar(archivo_actual, carpeta_entrada, carpeta_salida)
                
                time.sleep(1) 

            except subprocess.CalledProcessError as e:
                print("\n" + "!"*60)
                print(f"ERROR FATAL: La ejecución de '{nombre_script}' falló.")
                if e.stderr and e.stderr.strip():
                    print("   Salida de error del subproceso:")
                    for linea in e.stderr.strip().splitlines():
                        print(f"     | {linea}")
                print("!"*60)
                sys.exit(1)

    print(f"\n{'*'*60}\n*** CICLOS COMPLETADOS. El archivo final está en: '{archivo_actual}' ***\n{'*'*60}")


if __name__ == "__main__":
    # Este bloque se asegura de que el script pueda ser llamado desde la línea de comandos
    # con los argumentos correctos.
    if len(sys.argv) < 4:
        print("Uso: python app_video.py <ruta_carpeta_entrada> <ruta_carpeta_salida> <numero_de_ciclos> [es_shorts]")
        sys.exit(1)

    carpeta_entrada_arg = sys.argv[1]
    carpeta_salida_arg  = sys.argv[2]
    try:
        numero_ciclos_arg = int(sys.argv[3])
    except ValueError:
        print("ERROR: El número de ciclos debe ser un número entero.")
        sys.exit(1)

    es_shorts_arg = len(sys.argv) >= 5 and sys.argv[4] == "1"

    main(carpeta_entrada_arg, carpeta_salida_arg, numero_ciclos_arg, es_shorts_arg)