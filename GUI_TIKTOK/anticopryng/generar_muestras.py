import os
import subprocess
import imageio_ffmpeg

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
base_dir = r"C:\IA\funcional\avatar_srt\avatar\GUI_TIKTOK\anticopryng"
webm_dir = os.path.join(base_dir, "recursos_webm")

os.makedirs(webm_dir, exist_ok=True)

samples = [
    {
        "name": "sample1_boom.webm",
        "vf": "drawtext=text='BOOM':fontcolor=yellow:fontsize=80:x='150-40*sin(t*5)':y='150-40*cos(t*5)'"
    },
    {
        "name": "sample2_flash.webm",
        "vf": "drawbox=x=50:y=50:w=200:h=200:color=red@0.8:t=fill:enable='lt(mod(t,0.5),0.25)'"
    },
    {
        "name": "sample3_wtf.webm",
        "vf": "drawtext=text='WTF':fontcolor=cyan:fontsize=100:x='t*100-50':y=100"
    }
]

for s in samples:
    out_path = os.path.join(webm_dir, s["name"])
    cmd = [
        ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=black@0:s=300x300:r=30:d=2",
        "-vf", s["vf"],
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", out_path
    ]
    subprocess.run(cmd)

print("WebMs generados exitosamente en recursos_webm")
