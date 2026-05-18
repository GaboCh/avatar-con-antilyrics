# 🧠 Face Swap API - Flask + FaceFusion

Este servicio permite realizar un intercambio de rostros (Face Swap) usando FaceFusion ejecutado mediante un archivo `.bat`.  
El backend está hecho con Flask y acepta archivos JPG (cara) y MP4 (video) para realizar el procesamiento.

---

## 🚀 Endpoint disponible

### `POST /swap`

Realiza el intercambio de rostro usando la imagen y el video proporcionados.

#### Parámetros:

- `face`: archivo `.jpg` con la cara que deseas colocar
- `video`: archivo `.mp4` donde se reemplazará el rostro

---

## 📂 Estructura esperada

```
facefussion/
├── app.py                      # Servicio Flask principal
├── run_facefusion.bat         # Ejecutable de FaceFusion
├── inputs/
│   ├── faces/                 # Caras subidas
│   └── videos/                # Videos subidos
├── outputs/
   └── videos/                # Resultados generados

```

---

## 📥 Ejemplo de uso con `curl`

```bash
curl -X POST http://localhost:5100/swap \
  -F "face=@inputs/faces/ejemplo.jpg" \
  -F "video=@inputs/videos/ejemplo.mp4" \
  -o video_swap.mp4
```

Esto:
- Envía `ejemplo.jpg` como la cara a usar
- Envía `ejemplo.mp4` como el video destino
- Descarga el resultado como `video_swap.mp4`

---

## 📦 Requisitos

- Python 3.8+ con Flask (`pip install flask`)
- FaceFusion instalado en Pinokio, accesible desde:
  ```
  C:\pinokio\api\facefusion-pinokio.git
  ```
- Archivo `run_facefusion.bat` funcional, que:
  - usa `foto_cara.jpg` y `video_prueba.mp4` como entrada
  - genera `video_swap.mp4` como salida

---

## 📝 Notas adicionales

- El resultado final también se guarda en `outputs/videos/` con nombre único.
- Si no se genera el video correctamente, se devuelve un error 500.
- El servicio está pensado para funcionar en desarrollo (`debug=True`).

---

## 👨‍💻 Ejecución del servidor Flask

```bash
python app.py
```

Luego accede en:  
```
http://localhost:5100/swap
```

---

## 📁 Salida esperada

El archivo final (`video_swap.mp4`) será devuelto como respuesta **y guardado localmente** en `outputs/videos/`.

---
