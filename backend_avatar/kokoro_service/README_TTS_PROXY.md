# 🎙️ TTS Proxy Service (Kokoro Wrapper)

Este servicio actúa como un proxy entre tu frontend o sistema (como Avatar) y el backend de Kokoro-TTS, proporcionando una API limpia y controlada para generar audios en español con diferentes voces.

---

## ✅ Endpoints disponibles

| Método | Endpoint                   | Descripción                                       |
|--------|----------------------------|---------------------------------------------------|
| POST   | `/generate`                | Inicia la generación y retorna el `event_id`     |
| GET    | `/get_path/<event_id>`     | Devuelve información del archivo generado        |
| POST   | `/download_from_url`       | Descarga el archivo generado por Kokoro          |
| POST   | `/generate_complete`       | Genera el audio, espera y lo descarga directamente |
| GET    | `/voices`                  | Lista las voces disponibles                      |
| GET    | `/health`                  | Verifica el estado del servicio                  |
| GET    | `/`                        | Muestra la documentación en JSON                 |

---

## 🔁 Flujo manual

### 1. 🎤 Generar audio (obtener `event_id`)
```bash
curl -X POST http://127.0.0.1:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola, soy Dora", "voice": "dora", "speed": 1.0, "format": "MP3"}'
```

### 2. ⌛ Verificar estado del audio
```bash
curl http://127.0.0.1:5000/get_path/<event_id>
```

### 3. ⬇️ Descargar el archivo final
```bash
curl -X POST http://127.0.0.1:5000/download_from_url \
  -H "Content-Type: application/json" \
  -d '{"file_url": "http://127.0.0.1:7860/file=outputs/audio/ef_dora_xxxx.mp3", "filename": "voz_dora.mp3"}' \
  --output voz_dora.mp3
```

---

## ⚡ Flujo automático

### 🎯 Usar `/generate_complete`
```bash
curl -X POST http://127.0.0.1:5000/generate_complete \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola mundo con Santa", "voice": "santa", "speed": 0.9, "format": "MP3"}' \
  --output santa_final.mp3
```

---

## 📚 Extras

### 🧑‍🎤 Obtener voces disponibles
```bash
curl http://127.0.0.1:5000/voices
```

### 🩺 Verificar salud del servicio
```bash
curl http://127.0.0.1:5000/health
```

### 🧾 Ver documentación del servicio
```bash
curl http://127.0.0.1:5000/
```

---

## 🗣️ Voces disponibles

- `dora` → 🇪🇸 🚺 Dora
- `alex` → 🇪🇸 🚹 Alex
- `santa` → 🇪🇸 🚹 Santa

---

## 🧠 Notas

- Asegúrate de que Kokoro-TTS esté corriendo en `http://127.0.0.1:7860`
- Puedes usar `voice` como clave (`dora`) o valor completo (`🇪🇸 🚺 Dora`)
- Velocidad recomendada: entre `0.85` y `1.1`
- Formatos soportados: `MP3` y `WAV`

---

