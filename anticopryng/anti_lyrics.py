import os
import subprocess
import random
import sys
import traceback
import math

def get_random_value(base, tolerance):
    """Genera un valor flotante aleatorio para los filtros."""
    return base + random.uniform(-tolerance, tolerance)

def procesar():
    """Aplica filtros de audio avanzados para ofuscar la detección de letras."""
    print("--- Iniciando Script 'anti_lyrics.py' ---")

    try:
        # --- 1. VERIFICAR EL ARCHIVO DE ENTRADA ---
        if len(sys.argv) < 2:
            print("ERROR FATAL: No se proporcionó la ruta del archivo a procesar.")
            sys.exit(1)
        src_path = sys.argv[1]
        if not os.path.exists(src_path):
            print(f"ERROR FATAL: El archivo de entrada no existe: {src_path}")
            sys.exit(1)
        print(f"   > Archivo a procesar: {os.path.basename(src_path)}")

        # --- 2. LOCALIZAR FFmpeg ---
        try:
            import imageio_ffmpeg
            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"   > FFmpeg encontrado en: {ffmpeg_cmd}")
        except ImportError:
            print("ERROR: No se pudo importar imageio_ffmpeg. Instalando...")
            subprocess.run([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"], check=True)
            import imageio_ffmpeg
            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"   > FFmpeg encontrado en: {ffmpeg_cmd}")

        # --- 3. CREAR CARPETA DE SALIDA SI NO EXISTE ---
        project_dir = os.path.dirname(__file__)
        carpeta_salida = os.path.join(project_dir, "videos_finales_procesados")
        os.makedirs(carpeta_salida, exist_ok=True)
        print(f"   > Carpeta de salida: {carpeta_salida}")

        # --- 4. BANCO DE ARMAS ANTI-LYRICS (SINTAXIS 100% CORRECTA) ---
        
        # Arma #1: Vibrato - Modula la frecuencia
        vibrato_freq = get_random_value(5.5, 1.5)
        vibrato_depth = get_random_value(0.3, 0.1)
        vibrato_filter = f"vibrato=f={vibrato_freq}:d={vibrato_depth}"
        
        # Arma #2: Chorus - Efecto de coro (SIN el parámetro 't' que causaba el error)
        chorus_in_gain = get_random_value(0.4, 0.1)
        chorus_out_gain = get_random_value(0.4, 0.1)
        chorus_delay = get_random_value(40, 10)
        chorus_decay = get_random_value(0.4, 0.1)
        chorus_speed = get_random_value(0.5, 0.2)
        chorus_depth = get_random_value(2, 0.5)
        # Sintaxis correcta: chorus=in_gain:out_gain:delay:decay:speed:depth
        chorus_filter = f"chorus={chorus_in_gain}:{chorus_out_gain}:{chorus_delay}:{chorus_decay}:{chorus_speed}:{chorus_depth}"
        
        # Arma #3: Equalizer - Modifica bandas de frecuencia (ganancia acotada para evitar
        # el error 'Assertion failed: el >= 0' en libmp3lame/psymodel)
        eq_freq = get_random_value(3000, 500)
        eq_width = get_random_value(1000, 200)
        eq_gain = get_random_value(0, 1.5)   # Solo positivo: -1.5 a +1.5 dB (seguro para lame)
        eq_filter = f"equalizer=f={eq_freq}:width_type=h:width={eq_width}:g={eq_gain}"
        
        # Arma #4: Tremolo - Modulación de amplitud (opcional, comentada para no sobrecargar)
        # tremolo_freq = get_random_value(4.5, 1.5)
        # tremolo_depth = get_random_value(0.3, 0.1)
        # tremolo_filter = f"tremolo=f={tremolo_freq}:d={tremolo_depth}"
        
        # Arma #5: Highpass/Lowpass - Filtros de paso (sutil)
        highpass_freq = get_random_value(80, 20)
        highpass_filter = f"highpass=f={highpass_freq}"
        
        # Combinamos las armas
        af_chain = f"{vibrato_filter},{chorus_filter},{eq_filter},{highpass_filter}"
        
        print(f"   > Cadena de filtros: {af_chain}")
        
        # --- 5. CONSTRUIR EL COMANDO FFmpeg ---
        base_name, extension = os.path.splitext(os.path.basename(src_path))
        dst_path = os.path.join(carpeta_salida, f"{base_name}_antilyrics{extension}")

        comando = []
        if extension.lower() == '.mp3':
            comando = [
                ffmpeg_cmd, "-y", "-i", src_path,
                "-map", "0:a",          # Solo stream de audio, descarta portada/imagen incrustada
                "-af", af_chain,
                "-c:a", "libmp3lame", "-b:a", "192k",
                "-map_metadata", "-1", dst_path
            ]
        elif extension.lower() == '.mp4':
            comando = [
                ffmpeg_cmd, "-y", "-i", src_path, "-af", af_chain,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-map_metadata", "-1", dst_path
            ]
        else:
            print(f"ERROR: Formato '{extension}' no soportado.")
            sys.exit(1)

        print("   > Comando FFmpeg:")
        print(f"     {' '.join(comando)}")

        # --- 6. EJECUTAR EL PROCESO ---
        print("   > Ejecutando FFmpeg... (esto puede tardar)")
        resultado = subprocess.run(
            comando, 
            check=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='ignore'
        )
        
        print("   > [ÉXITO] El filtro Anti-Lyrics se aplicó correctamente.")
        print(f"   > Archivo generado: {os.path.basename(dst_path)}")
        print(f"   > Ruta completa: {dst_path}")

    except subprocess.CalledProcessError as e:
        print("\n" + "!"*60)
        print("ERROR FATAL: FFmpeg falló.")
        print("Código de retorno:", e.returncode)
        if e.stderr:
            print("\n--- Salida de error ---")
            print(e.stderr)
        print("!"*60)
        sys.exit(1)
    except Exception as e:
        print("\n" + "!"*60)
        print("ERROR FATAL INESPERADO en anti_lyrics.py")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        print("\nTraceback completo:")
        traceback.print_exc()
        print("!"*60)
        sys.exit(1)

if __name__ == "__main__":
    procesar()