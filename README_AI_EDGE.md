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

```python
import torch

model.eval()
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    model,
    dummy_input,
    "pet_embedding.onnx",
    input_names=["image"],
    output_names=["embedding"],
    opset_version=17,
)
```

### TensorFlow / Keras → TFLite

```python
import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

with open("pet_embedding.tflite", "wb") as f:
    f.write(tflite_model)
```

### Cuantización recomendada

- **Dynamic range quantization**: reduce tamaño ~4x sin pérdida significativa.
- **Float16 quantization**: buena para GPUs móviles.
- **Integer quantization**: mejor rendimiento en CPU móvil, requiere calibración.

## Integración en Flutter

Instalar los paquetes necesarios:

```yaml
dependencies:
  image: ^4.0.0
  tflite_flutter: ^0.10.0
  onnxruntime: ^1.0.0      # Alternativa para ONNX
```

Flujo en código:

1. Obtener imagen desde cámara o galería.
2. Preprocesar con `package:image`.
3. Cargar el modelo con `tflite_flutter` o `onnxruntime`.
4. Ejecutar inferencia para obtener el embedding.
5. Enviar el embedding al endpoint `/api/v1/pets/identify` en el backend.

Ejemplo conceptual:

```dart
final interpreter = await Interpreter.fromAsset('pet_embedding.tflite');
final input = preprocess(image); // [1, 224, 224, 3]
final output = List.filled(1 * 128, 0.0).reshape([1, 128]);
interpreter.run(input, output);
final embedding = output.first;
```

## Backend y Almacenamiento

- El vector embedding se guarda en una columna `embedding vector(128)` o según dimensión elegida.
- La búsqueda se realiza con operadores de pgvector, por ejemplo:

```sql
SELECT id, name, 1 - (embedding <=> $1) AS similarity
FROM pets
ORDER BY embedding <=> $1
LIMIT 10;
```

- FastAPI expone únicamente endpoints ligeros para recibir embeddings y devolver coincidencias.
- El proceso de entrenamiento y exportación del modelo se hace fuera del flujo del backend, manteniéndolo desacoplado.

## Beneficios Económicos y Técnicos

- **$0 cost de servidor ML**: el modelo no se ejecuta en la nube.
- **Latencia reducida**: inferencia local sin round-trip de red.
- **Privacidad**: la imagen nunca sale del dispositivo; solo viaja el embedding.
- **Escalabilidad barata**: pgvector permite búsquedas vectoriales eficientes en la capa gratuita de Supabase.
- **Backend ultraligero**: FastAPI sin dependencias como PyTorch/Celery/Redis, apto para despliegue gratuito.
