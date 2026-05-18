import os
import subprocess
import sys
import shutil
import time

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DEL_PROYECTO = os.path.dirname(os.path.abspath(__file__))
CARPETA_ENTRADA = os.path.join(BASE_DEL_PROYECTO, "videos_finales")
CARPETA_SALIDA = os.path.join(BASE_DEL_PROYECTO, "videos_finales_procesados")

# --- CONFIGURACIÓN DEL SWITCH ---
BUCLE_BASICO = ["ai_studio_code.py", "ai_studio_code_potenciado.py"]
RECETAS = {
    "1": {
        "nombre": "Bucle Estándar (AI Studio -> Potenciado)",
        "scripts": BUCLE_BASICO
    },
    "2": {
        "nombre": "Bucle Completo (AI Studio -> Potenciado -> Anti-Lyrics)",
        "scripts": BUCLE_BASICO + ["anti_lyrics.py"]
    },
    "3": {
        "nombre": "Prueba Rápida: Ejecutar SOLO Anti-Lyrics",
        "scripts": ["anti_lyrics.py"]
    }
}

NUMERO_DE_CICLOS = 10

# --- FUNCIONES AUXILIARES ---
def preparar_entorno():
    print("--- Preparando Entorno de Trabajo ---")
    if not os.path.isdir(BASE_DEL_PROYECTO):
        print(f"ERROR FATAL: El directorio base no existe: {BASE_DEL_PROYECTO}")
        sys.exit(1)
    os.makedirs(CARPETA_ENTRADA, exist_ok=True)
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

def obtener_archivo_de_trabajo_inicial():
    try:
        archivos = [f for f in os.listdir(CARPETA_ENTRADA) if not f.startswith('.')]
        if len(archivos) != 1:
            print(f"ERROR: Se esperaba 1 solo archivo en '{CARPETA_ENTRADA}', pero se encontraron {len(archivos)}.")
            sys.exit(1)
        return os.path.join(CARPETA_ENTRADA, archivos[0])
    except FileNotFoundError:
        print(f"ERROR: El directorio de entrada '{CARPETA_ENTRADA}' no fue encontrado.")
        sys.exit(1)

def mover_y_actualizar(archivo_original_procesado):
    try:
        archivos_salida = [f for f in os.listdir(CARPETA_SALIDA) if not f.startswith('.')]
        if not archivos_salida:
            print("ERROR: El script trabajador no generó ningún archivo en la carpeta de salida.")
            sys.exit(1)
        
        archivos_salida.sort(key=lambda f: os.path.getmtime(os.path.join(CARPETA_SALIDA, f)))
        nombre_archivo_nuevo = archivos_salida[-1]
        
        ruta_origen = os.path.join(CARPETA_SALIDA, nombre_archivo_nuevo)
        ruta_destino = os.path.join(CARPETA_ENTRADA, nombre_archivo_nuevo)

        os.remove(archivo_original_procesado)
        shutil.move(ruta_origen, ruta_destino)
        
        for f in os.listdir(CARPETA_SALIDA):
            os.remove(os.path.join(CARPETA_SALIDA, f))
            
        return ruta_destino
    except Exception as e:
        print(f"ERROR durante la limpieza y movimiento de archivos: {e}")
        sys.exit(1)

# --- FLUJO DE TRABAJO PRINCIPAL ---
def main():
    preparar_entorno()
    
    print("\n" + "="*30)
    print("PANEL DE CONTROL DE PROCESAMIENTO")
    print("="*30)
    for key, value in RECETAS.items():
        print(f"  [{key}] - {value['nombre']}")
    
    opcion = input("Ingresa el número de la receta que quieres ejecutar: ")
    if opcion not in RECETAS:
        print("Opción no válida. Saliendo del programa.")
        sys.exit(1)
        
    receta_seleccionada = RECETAS[opcion]
    scripts_a_ejecutar = receta_seleccionada["scripts"]
    
    print(f"\n✅ Has elegido: '{receta_seleccionada['nombre']}'")
    print(f"   Scripts a ejecutar en cada ciclo: {scripts_a_ejecutar}")
    
    archivo_actual = obtener_archivo_de_trabajo_inicial()
    print(f"   Archivo inicial: {os.path.basename(archivo_actual)}")

    for i in range(NUMERO_DE_CICLOS):
        print(f"\n{'='*60}\n=== INICIANDO CICLO {i + 1}/{NUMERO_DE_CICLOS} ===\n{'='*60}")
        for script in scripts_a_ejecutar:
            print(f"\n--> Ejecutando '{script}' sobre '{os.path.basename(archivo_actual)}'")
            comando = [sys.executable, os.path.join(BASE_DEL_PROYECTO, script), archivo_actual]
            
            try:
                # CAMBIO CLAVE: text=True para capturar correctamente la salida
                resultado = subprocess.run(
                    comando, 
                    check=True, 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    stdin=subprocess.DEVNULL
                )
                
                stdout = resultado.stdout.strip()
                if stdout:
                    print("   Salida del script:")
                    for linea in stdout.splitlines(): 
                        print(f"     | {linea}")
                
                print(f"   [ÉXITO] '{script}' finalizó.")
                print("   Actualizando archivo de trabajo...")
                archivo_actual = mover_y_actualizar(archivo_actual)
                print(f"   Nuevo archivo de trabajo: '{os.path.basename(archivo_actual)}'")
                time.sleep(1)
            except KeyboardInterrupt:
                # En Windows, el primer lanzamiento de FFmpeg puede generar esta señal espuria
                print(f"   [AVISO] Señal espuria ignorada. Verificando si el archivo fue generado...")
                archivo_actual = mover_y_actualizar(archivo_actual)
                time.sleep(1)
            except subprocess.CalledProcessError as e:
                print("\n" + "!"*60)
                print(f"ERROR FATAL: La ejecución de '{script}' falló.")
                print(f"Código de retorno: {e.returncode}")
                
                # CAMBIO CLAVE: Mostrar AMBAS salidas (stdout Y stderr)
                if e.stdout and e.stdout.strip():
                    print("\n--- Salida Estándar (stdout) ---")
                    for linea in e.stdout.strip().splitlines():
                        print(f"  {linea}")
                
                if e.stderr and e.stderr.strip():
                    print("\n--- Salida de Error (stderr) ---")
                    for linea in e.stderr.strip().splitlines():
                        print(f"  {linea}")
                
                if not (e.stdout and e.stdout.strip()) and not (e.stderr and e.stderr.strip()):
                    print("El subproceso no produjo ninguna salida visible.")
                
                print("!"*60)
                sys.exit(1)

    print(f"\n{'*'*60}\n*** PROCESO COMPLETADO EXITOSAMENTE ***\nEl archivo final es: '{archivo_actual}'\n{'*'*60}")

if __name__ == "__main__":
    main()