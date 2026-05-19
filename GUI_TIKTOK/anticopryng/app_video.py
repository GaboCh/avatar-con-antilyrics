import os
import subprocess
import sys
import shutil
import glob
import time

# --- SCRIPT PORTABLE - SIN RUTAS FIJAS ---
# Llamado por la GUI de Gradio con 4 argumentos:
#   sys.argv[1] = carpeta de entrada (contiene el .mp4 a procesar)
#   sys.argv[2] = carpeta de salida  (donde el worker deposita el resultado)
#   sys.argv[3] = numero de ciclos
#   sys.argv[4] = "1" si es Shorts, "0" si no
#
# Los scripts trabajadores estan en la misma carpeta que este script.

SCRIPTS_DIR = os.path.abspath(os.path.dirname(__file__))

SCRIPTS_TRABAJADOR = [
    "ai_studio_code_video.py",    # Aplica EstÃ©tica Premium (Grain, Vignette, Temp, Crop)
    "ai_studio_code_potenciado_video.py", # Aplica ecualizaciÃ³n fina y mÃ¡s sutiles
]


def main(carpeta_entrada, carpeta_salida, num_ciclos, es_shorts):
    print("--- Preparando Entorno de Trabajo para el Subproceso ---")

    if not os.path.isdir(SCRIPTS_DIR):
        print(f"ERROR: El directorio base de los scripts no existe: {SCRIPTS_DIR}")
        sys.exit(1)
    print(f"Directorio base de scripts encontrado: {SCRIPTS_DIR}")

    os.makedirs(carpeta_entrada, exist_ok=True)
    os.makedirs(carpeta_salida, exist_ok=True)
    print(f"Directorios de trabajo listos: "
          f"'{os.path.basename(carpeta_entrada)}' y '{os.path.basename(carpeta_salida)}'")

    # Buscar el archivo .mp4 inicial en la carpeta de entrada
    archivos = glob.glob(os.path.join(carpeta_entrada, "*.mp4"))
    if not archivos:
        print(f"ERROR: No se encontro ningun .mp4 en '{carpeta_entrada}'")
        sys.exit(1)
    if len(archivos) > 1:
        print(f"ERROR: Se esperaba 1 .mp4 en '{carpeta_entrada}', "
              f"se encontraron {len(archivos)}: {[os.path.basename(a) for a in archivos]}")
        sys.exit(1)

    archivo_actual = archivos[0]
    print(f"Archivo inicial para procesar: {archivo_actual}")

    def correr_worker(nombre_script, arch_actual):
        ruta_script = os.path.join(SCRIPTS_DIR, nombre_script)
        if not os.path.exists(ruta_script):
            print(f"ERROR FATAL: No se encuentra el script: {ruta_script}")
            sys.exit(1)
        print(f"\n--> Paso: Ejecutando '{nombre_script}'...")
        cmd = [sys.executable, "-u", ruta_script, carpeta_entrada, carpeta_salida]
        try:
            resultado = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            print(f"'{nombre_script}' finalizo exitosamente.")
            if resultado.stdout and resultado.stdout.strip():
                print("   Salida del script trabajador:")
                for linea in resultado.stdout.strip().splitlines():
                    print(f"     | {linea}")
        except subprocess.CalledProcessError as e:
            print(f"\n{'!'*60}\nERROR FATAL: La ejecucion de '{nombre_script}' fallo.")
            if e.stderr and e.stderr.strip():
                print("   Salida de error del subproceso:")
                for linea in e.stderr.strip().splitlines():
                    print(f"     | {linea}")
            print(f"{'!'*60}\n")
            sys.exit(1)

        print("\n   Actualizando archivo de trabajo para el siguiente paso...")
        archivos_salida = glob.glob(os.path.join(carpeta_salida, "*.mp4"))
        if not archivos_salida:
            print(f"ERROR: El script trabajador no genero ningun .mp4 en '{carpeta_salida}'")
            sys.exit(1)
        nombre_nuevo  = os.path.basename(archivos_salida[0])
        destino_nuevo = os.path.join(carpeta_entrada, nombre_nuevo)
        print(f"   [ACCION] Borrando archivo antiguo: {arch_actual}")
        os.remove(arch_actual)
        print(f"   [ACCION] Moviendo '{archivos_salida[0]}' a '{destino_nuevo}'")
        shutil.move(archivos_salida[0], destino_nuevo)
        time.sleep(0.5)
        return destino_nuevo

    # === FASE UNICA: CICLOS DE EFECTOS SUTILES ===
    for i in range(num_ciclos):
        print(f"\n{'='*60}\n=== INICIANDO CICLO {i+1}/{num_ciclos} ===\n{'='*60}")
        for nombre_script in SCRIPTS_TRABAJADOR:
            archivo_actual = correr_worker(nombre_script, archivo_actual)

    print(f"\n{'*'*60}")
    print(f"*** CICLOS COMPLETADOS. El archivo final esta en: '{archivo_actual}' ***")
    print(f"{'*'*60}")


if __name__ == "__main__":
    print("\n>>> ENTRO A APP_VIDEO (Efectos Sutiles) <<<")
    # ============================================================
    # >>> CONFIGURA AQUÃ TUS CICLOS POR DEFECTO <<<
    # ============================================================
    NUM_CICLOS_POR_DEFECTO = 4 #Cambia este numero por los ciclos que quieras
    # ============================================================

    if len(sys.argv) < 3:
        print("Uso: python app_video.py <carpeta_entrada> <carpeta_salida> [num_ciclos] [es_shorts]")
        print("     Ejemplo: python app_video.py ./videos_finales ./videos_finales_procesados")
        sys.exit(1)

    # Si pasan el argumento lo usamos, si no, usamos el valor por defecto de arriba
    ciclos = int(sys.argv[3]) if len(sys.argv) >= 4 else NUM_CICLOS_POR_DEFECTO
    shorts = (sys.argv[4] == "1") if len(sys.argv) >= 5 else False

    main(
        carpeta_entrada=sys.argv[1],
        carpeta_salida=sys.argv[2],
        num_ciclos=ciclos,
        es_shorts=shorts,
    )