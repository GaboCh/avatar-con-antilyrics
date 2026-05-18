import os
import subprocess
import sys
import shutil
import time

# --- CONFIGURACIÓN DE RUTAS ABSOLUTAS ---
# Se define la ruta base del proyecto.
# ATENCIÓN: La 'r' antes de las comillas es importante en Windows para que
# las barras invertidas '\' se interpreten correctamente.
BASE_DEL_PROYECTO = r"C:\Users\gabrielchalcog\proyectos\IA\avatar_srt\avatar\anticopryng"

# Se construyen las rutas completas a las carpetas de trabajo usando la ruta base.
CARPETA_ENTRADA = os.path.join(BASE_DEL_PROYECTO, "videos_finales")
CARPETA_SALIDA = os.path.join(BASE_DEL_PROYECTO, "videos_finales_procesados")

# --- CONFIGURACIÓN DEL PROCESO ---

# 1. Lista de nombres de los scripts "trabajadores". El código los buscará en BASE_DEL_PROYECTO.
SCRIPTS_TRABAJADOR = [
    "ai_studio_code_video.py",
    "ai_studio_code_potenciado_video.py",
]

# 2. Número de veces que se repetirá el ciclo completo de ejecución.
NUMERO_DE_CICLOS = 5


# --- FUNCIONES AUXILIARES ---

def preparar_entorno():
    """Asegura que las rutas y directorios existan antes de empezar."""
    print("--- Preparando Entorno de Trabajo ---")
    if not os.path.isdir(BASE_DEL_PROYECTO):
        print(f"ERROR FATAL: El directorio base del proyecto no existe en la ruta especificada.")
        print(f"Ruta buscada: {BASE_DEL_PROYECTO}")
        sys.exit(1)
        
    print(f"Directorio base encontrado: {BASE_DEL_PROYECTO}")
    
    os.makedirs(CARPETA_ENTRADA, exist_ok=True)
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    print(f"Directorios '{os.path.basename(CARPETA_ENTRADA)}' y '{os.path.basename(CARPETA_SALIDA)}' listos.")

def obtener_archivo_de_trabajo_inicial():
    """
    Localiza y devuelve la ruta completa del único archivo en la carpeta de entrada.
    Si no hay exactamente un archivo, el programa termina con un error.
    """
    try:
        archivos = os.listdir(CARPETA_ENTRADA)
        if len(archivos) == 0:
            print(f"ERROR: No se encontró ningún archivo en la carpeta '{CARPETA_ENTRADA}'.")
            sys.exit(1)
        if len(archivos) > 1:
            print(f"ERROR: Se esperaba 1 solo archivo en '{CARPETA_ENTRADA}', pero se encontraron {len(archivos)}.")
            sys.exit(1)
        
        # Construye la ruta completa (absoluta) al archivo.
        ruta_completa_archivo = os.path.join(CARPETA_ENTRADA, archivos[0])
        print(f"Archivo inicial para procesar: {ruta_completa_archivo}")
        return ruta_completa_archivo
    except FileNotFoundError:
        print(f"ERROR: El directorio de entrada '{CARPETA_ENTRADA}' no fue encontrado.")
        sys.exit(1)

def mover_y_actualizar(archivo_original_procesado):
    """
    Mueve el resultado de la carpeta de salida a la de entrada y elimina el archivo original.
    Devuelve la nueva ruta completa del archivo de trabajo.
    """
    try:
        archivos_salida = os.listdir(CARPETA_SALIDA)
        if not archivos_salida:
            print(f"ERROR: El script trabajador no generó ningún archivo en '{CARPETA_SALIDA}'.")
            sys.exit(1)

        nombre_archivo_nuevo = archivos_salida[0]
        ruta_origen_nuevo = os.path.join(CARPETA_SALIDA, nombre_archivo_nuevo)
        ruta_destino_nuevo = os.path.join(CARPETA_ENTRADA, nombre_archivo_nuevo)

        # 1. Eliminar el archivo antiguo (ya procesado) de la carpeta de entrada.
        # --- PRINT AÑADIDO ---
        print(f"   [ACCIÓN] A punto de borrar el archivo antiguo: {archivo_original_procesado}")
        os.remove(archivo_original_procesado)
        # --- PRINT AÑADIDO ---
        print(f"   [CONFIRMACIÓN] Archivo borrado exitosamente.")


        # 2. Mover el nuevo archivo modificado a la carpeta de entrada.
        # --- PRINT AÑADIDO ---
        print(f"   [ACCIÓN] A punto de mover '{ruta_origen_nuevo}' a '{ruta_destino_nuevo}'")
        shutil.move(ruta_origen_nuevo, ruta_destino_nuevo)
        # --- PRINT AÑADIDO ---
        print(f"   [CONFIRMACIÓN] Archivo movido exitosamente.")
        
        return ruta_destino_nuevo

    except Exception as e:
        print(f"ERROR durante la limpieza y movimiento de archivos: {e}")
        sys.exit(1)


# --- FLUJO DE TRABAJO PRINCIPAL ---

def main():
    """
    Función principal que orquesta todo el flujo de trabajo.
    """
    preparar_entorno()
    
    archivo_actual = obtener_archivo_de_trabajo_inicial()

    # Bucle Externo: Repite todo el proceso N veces
    for i in range(NUMERO_DE_CICLOS):
        print(f"\n{'='*60}\n=== INICIANDO CICLO DE PROCESAMIENTO {i + 1}/{NUMERO_DE_CICLOS} ===\n{'='*60}")

        # Bucle Interno: Ejecuta cada script trabajador en orden
        for nombre_script in SCRIPTS_TRABAJADOR:
            ruta_script_completa = os.path.join(BASE_DEL_PROYECTO, nombre_script)
            
            if not os.path.exists(ruta_script_completa):
                print(f"\nERROR FATAL: El script trabajador '{nombre_script}' no se encuentra en la ruta:")
                print(f"{ruta_script_completa}")
                sys.exit(1)

            print(f"\n--> Paso: Ejecutando '{nombre_script}' sobre '{os.path.basename(archivo_actual)}'")
            
            comando = [sys.executable, ruta_script_completa, archivo_actual]
            
            try:
                # Ejecuta el subproceso
                resultado = subprocess.run(
                    comando,
                    check=True,
                    stdin=subprocess.DEVNULL
                    #capture_output=True,
                    #text=False
                )
                
                # --- PRINT AÑADIDO ---
                print(f"   [CONFIRMACIÓN] El subproceso '{nombre_script}' se ha ejecutado y ha finalizado.")
                
                #stdout_str = resultado.stdout.decode('utf-8', errors='ignore').strip()
                #print(f"'{nombre_script}' finalizó exitosamente.")
                #if stdout_str:
                #    print("   Salida del script trabajador:")
                #    for linea in stdout_str.splitlines():
                #        print(f"     | {linea}")

                print("\n   Actualizando archivo de trabajo para el siguiente paso...")
                archivo_actual = mover_y_actualizar(archivo_actual)
                
                time.sleep(1) 
            except KeyboardInterrupt:
                # En Windows, el primer lanzamiento de FFmpeg puede generar esta señal espuria
                print(f"   [AVISO] Señal espuria ignorada. Verificando si el archivo fue generado...")
                archivo_actual = mover_y_actualizar(archivo_actual)
                time.sleep(1)
            except subprocess.CalledProcessError as e:
                #stderr_str = e.stderr.decode('utf-8', errors='ignore').strip()
                print("\n" + "!"*60)
                print(f"ERROR FATAL: La ejecución de '{nombre_script}' falló.")
                print(f"Código de retorno: {e.returncode}")
                #if stderr_str:
                #    print("   Salida de error del subproceso:")
                #    for linea in stderr_str.splitlines():
                #        print(f"     | {linea}")
                print("!"*60)
                sys.exit(1)

    print(f"\n{'*'*60}\n*** PROCESO COMPLETADO EXITOSAMENTE DESPUÉS DE {NUMERO_DE_CICLOS} CICLOS ***")
    print(f"El archivo final se encuentra en: '{archivo_actual}'")
    print(f"{'*'*60}")


if __name__ == "__main__":
    main()