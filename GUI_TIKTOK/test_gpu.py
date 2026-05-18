import sys
sys.path.insert(0, r'C:\IA\2026CODE V1\2026CODE\avatar_srt\avatar\GUI_TIKTOK\anticopryng')

from ai_studio_code_video import detectar_encoder
import imageio_ffmpeg

ff = imageio_ffmpeg.get_ffmpeg_exe()
print("FFmpeg:", ff)
enc = detectar_encoder(ff)
print("Encoder detectado:", enc)
