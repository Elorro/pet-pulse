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

## 🗄️ Esquema de la base de datos

Supabase es la fuente de verdad del esquema. Cada cambio vive como un archivo SQL en
`supabase/migrations/` y se aplica con la CLI de Supabase; ya no se usa Alembic.

- **Nuevo cambio:** `supabase migration new <nombre>`, escribe el SQL y abre un PR.
- **Aplicarlo en producción:** `supabase link --project-ref <ref>` y luego `supabase db push`.
- **No edites tablas desde el dashboard** sin crear también la migración; si ocurre, captúralo
  con `supabase db pull` para que el repositorio no se desincronice.
- Los modelos de `app/infrastructure/db/models/` deben reflejar estas tablas. Las pruebas crean
  las tablas desde los modelos (SQLite), así que un modelo desalineado no falla en las pruebas
  pero sí en producción.

## 📂 Documentación Adicional

- [Guía de IA y Edge Computing](README_AI_EDGE.md)
- [Especificación de la Arquitectura Móvil](README_MOBILE.md)
