import os
import subprocess
import glob
import random

# --- CONFIGURACION ---
CARPETA_ENTRADA = r"C:\IA\funcional\avatar_srt\avatar\GUI_TIKTOK\anticopryng\videos_finales"
CARPETA_SALIDA  = r"C:\IA\funcional\avatar_srt\avatar\GUI_TIKTOK\anticopryng\videos_finales_procesados"

# <<< CAMBIA AQUI EL MODO PARA PROBAR >>>
# Opciones: "fondo_fractal", "overlay_matrix", "split_screen", "neuro_tiktok", "hyper_tiktok"
MODO = "hyper_tiktok"

import imageio_ffmpeg
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

videos = glob.glob(os.path.join(CARPETA_ENTRADA, "*.mp4"))
if not videos:
    print(f"ERROR: No hay .mp4 en {CARPETA_ENTRADA}")
    exit(1)

src = videos[0]
print(f"Procesando: {os.path.basename(src)}")
os.makedirs(CARPETA_SALIDA, exist_ok=True)

cmd = []
dst = os.path.join(CARPETA_SALIDA, f"TEST_{MODO.upper()}.mp4")

if MODO == "hyper_tiktok":
    # 1. Cortes y Speed Ramps en el video principal (Top)
    # 2. Fondo Plasma Matemático en el fondo (Bottom)
    # 3. Overlays Reactivos Simulados (Cuadros de colores semitransparentes parpadeando)
    
    duracion_total = 74.0 # Duración del video original (1:14)
    
    fc_parts = []
    
    # 1. Video original intacto para la mitad superior (sin trim para que pase entero)
    fc_parts.append("[0:v]scale=720:640,setsar=1[v_concat];")
    # Audio original
    fc_parts.append("[0:a]anull[outa];")
    
    # 2. Generar Fondo de Mandelbrot (Rápido) para la parte inferior (720x640)
    fc_parts.append(
        f"mandelbrot=size=720x640:rate=30,trim=duration={duracion_total}[plasma];"
    )
    
    # 3. Unir Video Intacto (Arriba) con Plasma (Abajo)
    fc_parts.append("[v_concat][plasma]vstack=inputs=2[split_screen];")
    
    # 4. Overlays Reactivos (Simulación de GIFs)
    # Generamos 15 cuadrados de colores semitransparentes en tiempos aleatorios
    overlay_filters = "[split_screen]"
    for i in range(15):
        t_start = random.uniform(1.0, duracion_total - 1.0)
        t_end = t_start + random.uniform(0.3, 0.8) # Duran entre 0.3s y 0.8s
        x = random.randint(50, 500)
        y = random.randint(100, 1000)
        color = random.choice(["red@0.7", "blue@0.7", "yellow@0.7", "green@0.7"])
        
        # Dibujamos un cuadro para simular la aparición del GIF
        overlay_filters += f"drawbox=x={x}:y={y}:w=200:h=200:color={color}:t=fill:enable='between(t,{t_start:.1f},{t_end:.1f})'"
        if i < 14:
            overlay_filters += ","
            
    overlay_filters += "[outv]"
    fc_parts.append(overlay_filters)
    
    fc = "".join(fc_parts)
    
    cmd = [
        ffmpeg, "-y", "-i", src,
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", dst
    ]

elif MODO == "neuro_tiktok":
    # Estructura: Cortes cada 1.5 - 2.5s, flash negro de 3 frames (0.1s),
    # speed ramps aleatorios (1.0x o 1.25x), y micro zooms para movimiento constante.
    
    # NOTA: Para no requerir ffprobe y simplificar el test, procesaremos solo los
    # primeros 15 segundos del video de entrada o hasta que se acabe.
    duracion_total = 15.0
    t_actual = 0.0
    segmentos = []
    
    while t_actual < duracion_total:
        dur_clip = random.uniform(1.5, 2.5)
        if t_actual + dur_clip > duracion_total:
            dur_clip = duracion_total - t_actual
            
        segmentos.append({
            'inicio': t_actual,
            'duracion': dur_clip,
            'zoom': random.uniform(1.05, 1.25),
            'speed': random.choice([1.0, 1.25])
        })
        t_actual += dur_clip

    fc_parts = []
    concat_v = ""
    concat_a = ""
    
    for i, seg in enumerate(segmentos):
        start = seg['inicio']
        dur = seg['duracion']
        speed = seg['speed']
        z = seg['zoom']
        
        # Efectos de Video: trim, setpts (para la velocidad real), scale+crop para el micro zoom
        v_filter = (
            f"[0:v]trim=start={start}:duration={dur},setpts=PTS-STARTPTS,"
            f"setpts={(1.0/speed):.3f}*PTS,"
            f"scale=720*{z}:1280*{z},crop=720:1280,setsar=1[v{i}];"
        )
        
        # Efectos de Audio: atrim, asetpts, atempo
        a_filter = (
            f"[0:a]atrim=start={start}:duration={dur},asetpts=PTS-STARTPTS,"
            f"atempo={speed}[a{i}];"
        )
        
        fc_parts.append(v_filter)
        fc_parts.append(a_filter)
        
        concat_v += f"[v{i}]"
        concat_a += f"[a{i}]"
        
        # Insertar flash negro entre cortes
        if i < len(segmentos) - 1:
            # Video negro puro de 0.1s (aprox 3 frames a 30fps)
            fc_parts.append(f"color=black:size=720x1280:rate=30:d=0.1[black{i}];")
            concat_v += f"[black{i}]"
            
            # Audio silencioso para emparejar con el video negro
            fc_parts.append(f"anullsrc=r=48000:cl=stereo:d=0.1[silence{i}];")
            concat_a += f"[silence{i}]"

    n_concat = len(segmentos) * 2 - 1
    fc_parts.append(f"{concat_v}concat=n={n_concat}:v=1:a=0[outv];")
    fc_parts.append(f"{concat_a}concat=n={n_concat}:v=0:a=1[outa]")
    
    fc = "".join(fc_parts)
    
    cmd = [
        ffmpeg, "-y", "-i", src,
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", dst
    ]

elif MODO == "fondo_plasma":
    # Genera un fondo de plasma fluyendo infinitamente (matematico)
    # y pone el video original escalado al 85% encima.
    fc = (
        "color=black:size=720x1280:rate=30[bg_base];"
        "[bg_base]geq=r='128+128*sin(X/50+T)':g='128+128*sin(Y/50+T)':b='128+128*sin((X+Y)/50+T)'[fondo_raw];"
        "[fondo_raw]format=yuv420p,boxblur=10:5,eq=saturation=1.5:brightness=-0.1[fondo];"
        "[0:v]scale=iw*0.85:ih*0.85,format=yuva420p[fg];"
        "[fondo][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[out]"
    )
    cmd = [
        ffmpeg, "-y", "-i", src,
        "-filter_complex", fc,
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "copy", dst
    ]

elif MODO == "overlay_matrix":
    # 1. Genera el Juego de la Vida (Autómata celular tipo ASCII/Matrix)
    # 2. Lo mezcla por encima del video en modo pantalla (suave)
    rand_rule = random.choice(["B3/S23", "B36/S23"]) # Reglas matematicas
    fc = (
        f"life=size='720x1280':rate=30:rule={rand_rule}:ratio=0.1[life_raw];"
        "[life_raw]format=yuv420p,colorkey=black:0.1:0.1,colorchannelmixer=rr=0:gg=1:bb=0[matrix];"
        "[0:v][matrix]overlay=shortest=1:format=auto[out]"
    )
    cmd = [
        ffmpeg, "-y", "-i", src,
        "-filter_complex", fc,
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "copy", dst
    ]

elif MODO == "split_screen":
    # 1. Genera fractal para la parte de abajo
    # 2. Corta el video original para que entre arriba (Split screen)
    fc = (
        f"mandelbrot=size='720x500':rate=30[gameplay];"
        "[0:v]scale=720:1280,crop=720:780:0:0[top];"
        "[top][gameplay]vstack=inputs=2[out]"
    )
    cmd = [
        ffmpeg, "-y", "-i", src,
        "-filter_complex", fc,
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "copy", dst
    ]

print(f"Modo: {MODO}")
print("Ejecutando FFmpeg... (esto puede tardar unos segundos)")

r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
if r.returncode == 0:
    print(f"\n[OK] Video generado en: {dst}")
else:
    print(f"\n[ERROR] FFmpeg fallo:")
    print(r.stderr[-2000:])
