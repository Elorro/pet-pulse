# Pet Pulse API

**Pet Pulse** es una API REST para una red social de mascotas, enfocada en compartir publicaciones y conectar a una comunidad interesada en su cuidado, rescate y adopción.

## Funcionalidades

- Registro e inicio de sesión, renovación de sesión y cierre de sesión mediante **Supabase Auth**.
- Consulta del perfil asociado al usuario autenticado.
- Creación y consulta paginada de publicaciones.
- Comentarios en publicaciones, con opción de adjuntar imágenes.
- Likes por usuario, con consulta y opción para quitarlos.
- Carga de imágenes mediante URLs firmadas y almacenamiento en Supabase Storage.

## Tecnologías

- **Python** y **FastAPI** para una API asíncrona y tipada.
- **SQLAlchemy** para el acceso a datos.
- **PostgreSQL y Supabase** para persistencia, autenticación y almacenamiento.
- **Pydantic** para validar solicitudes y respuestas.
- **Pytest** para pruebas unitarias e integración.

## Arquitectura

La API organiza el código en capas de rutas, dominio, interfaces y servicios de infraestructura. Esta separación mantiene la lógica del producto desacoplada de la base de datos y de servicios externos como Supabase.

Los endpoints están versionados bajo `/api/v1` y la documentación interactiva se genera con OpenAPI y FastAPI.

## Seguridad y validación

- Los endpoints que modifican contenido requieren autenticación mediante token Bearer de Supabase.
- Las solicitudes se validan con esquemas tipados y límites de longitud.
- Las cargas de imágenes aceptan tipos permitidos y verifican adjuntos de comentarios de hasta 5 MiB.
- La API configura CORS y cabeceras de seguridad; en producción puede forzar HTTPS.

## Reconocimiento de mascotas

El proyecto contempla una futura función de reconocimiento biométrico mediante embeddings generados en el dispositivo móvil y comparados en el backend. **Esa capacidad está planteada en la documentación, pero no forma parte de los endpoints implementados actualmente.**

## Estado del proyecto

La API cubre actualmente autenticación, perfiles, publicaciones, comentarios, likes y carga de imágenes. La interfaz web se desarrolla en un proyecto separado.

## Tecnologías clave

`Python` · `FastAPI` · `SQLAlchemy` · `PostgreSQL` · `Supabase` · `Pydantic` · `Pytest`
