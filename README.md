# 🐾 Pet Pulse

Red social de código abierto para mascotas orientada al rescate, foro y adopción, con un sistema biométrico avanzado de reconocimiento canino/felino mediante embeddings vectoriales.

> **Nota para desarrollo local:**  
> Por defecto, el entorno de desarrollo usa **SQLite** para simplificar las pruebas.  
> La configuración de producción puede seguir usando **PostgreSQL + pgvector** sin cambios adicionales.

## 🚀 Características Principales (Fases)

- **Fase 1 (Foro MVP):** Publicaciones, comentarios, reacciones y compartidos optimizados.
- **Fase 2 (Comunidad de Rescate):** Módulos integrados para reportes de adopción y mascotas extraviadas.
- **Fase 3 (Edge AI Biométrico):** Reconocimiento animal mediante comparación de vectores de distancia de coseno nativa.

## 🛠️ Stack Tecnológico (Costo $0 USD de Infraestructura)

- **Backend API:** Python 3.11+ con FastAPI (asíncrono, robusto y tipado).
- **Base de Datos & Vector Store:**
  - **Desarrollo local:** SQLite (sin servidor, ideal para pruebas)
  - **Producción/Cloud:** PostgreSQL 15+ con extensión pgvector (Capa gratuita en Supabase)
- **Frontend Móvil:** Flutter (Dart) para compilación nativa en Android (F-Droid/APK) e iOS.
- **Cómputo de IA en el Dispositivo (Edge ML):** Exportación de modelos a formatos ONNX / TFLite para ejecución local en el celular del usuario final, liberando de costos al servidor web.

## 🛡️ Pilares de Seguridad de Producción Real

El sistema está diseñado bajo una lista estricta de **20 parámetros de seguridad industrial**, que incluyen:

- Ocultación y rotación segura de API keys y secretos.
- Hasheo de contraseñas con bcrypt.
- Row-Level Security (RLS) en PostgreSQL.
- Rate limiting para mitigar abusos y fuerza bruta.
- Sanitización de contenido y validación de entradas.
- Parametrización de consultas mediante ORM contra inyecciones SQL.
- Principio de mínima exposición en endpoints y dependencias.
- Uso estricto de HTTPS y políticas CORS.
- Auditoría y trazabilidad de eventos críticos.
- Configuración mediante variables de entorno validadas.

## 📂 Documentación Adicional

- [Guía de IA y Edge Computing](README_AI_EDGE.md)
- [Especificación de la Arquitectura Móvil](README_MOBILE.md)
