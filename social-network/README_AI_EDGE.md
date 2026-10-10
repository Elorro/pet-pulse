# Estrategia de IA en el Edge: Reconocimiento Biométrico de Mascotas

## Objetivo

Mantener los costos del servidor en **$0 USD** moviendo la inferencia del modelo de visión por computadora al dispositivo móvil. El backend FastAPI solo almacenará y comparará embeddings vectoriales de forma ligera usando PostgreSQL + pgvector.

## Arquitectura General

1. **Dispositivo móvil (Flutter)**
   - Captura la imagen de la mascota con la cámara.
   - Preprocesa la imagen (redimensionar, normalizar, recortar rostro).
   - Ejecuta el modelo de embedding en formato **ONNX** o **TFLite**.
   - Genera un vector embedding compacto (e.g., 128/256 dimensiones).
   - Envía únicamente el embedding al backend.

2. **Backend FastAPI**
   - Recibe el embedding y lo compara con los vectores almacenados en PostgreSQL usando pgvector.
   - Devuelve coincidencias por similitud coseno o distancia euclidiana.
   - No ejecuta ningún modelo pesado.

## Selección del Modelo

Se recomienda partir de un modelo tipo **MobileNetV3** o **FaceNet** adaptado para mascotas, ya que ofrecen buen equilibrio entre precisión y tamaño para móviles.

| Modelo candidato       | Tamaño aprox. | Embedding dims |
|------------------------|---------------|----------------|
| MobileNetV3-Small      | 1.5-3 MB       | 256            |
| FaceNet-MobileNet      | 4-8 MB         | 128            |
| EfficientNet-Lite0     | 3-5 MB         | 128            |

Tras el entrenamiento o fine-tuning, se procede a exportarlo.

## Exportación a ONNX / TFLite

### PyTorch → ONNX

