# 🐾 PetPulse (social-network)

Red social de código abierto para mascotas orientada al rescate, foro y adopción, con un sistema biométrico avanzado de reconocimiento canino/felino mediante embeddings vectoriales.

## 🚀 Características Principales (Fases)

- **Fase 1 (Foro MVP):** Publicaciones, comentarios, reacciones y compartidos optimizados.
- **Fase 2 (Comunidad de Rescate):** Módulos integrados para reportes de adopción y mascotas extraviadas.
- **Fase 3 (Edge AI Biométrico):** Reconocimiento animal mediante comparación de vectores de distancia de coseno nativa.

## 🛠️ Stack Tecnológico (Costo $0 USD de Infraestructura)

- **Backend API:** Python 3.11+ con FastAPI (asíncrono, robusto y tipado).
- **Base de Datos & Vector Store:** PostgreSQL 15+ con extensión pgvector (Capa gratuita en Supabase).
- **Frontend Móvil:** Flutter (Dart) para compilación nativa en Android (F-Droid/APK) e iOS.
- **Cómputo de IA en el Dispositivo (Edge ML):** Exportación de modelos a formatos ONNX / TFLite para ejecución local en el celular del usuario final, liberando de costos al servidor web.

## 🧭 Guía de Configuración

Ver [docs/SETUP.md](docs/SETUP.md) para el estado actual del backend, la decisión de arquitectura con Supabase y los pasos de instalación.

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

- [Guía de IA y Edge Computing](social-network/README_AI_EDGE.md)
- [Especificación de la Arquitectura Móvil](social-network/README_MOBILE.md)
