# Pet Pulse - Móvil (Flutter)

Este documento describe la arquitectura limpia para la aplicación móvil desarrollada en Flutter, la cual consume la API REST creada con FastAPI.

## Estructura de carpetas propuesta para Flutter

lib/
├── main.dart
├── app/
│   ├── config/               # Configuración de entorno, rutas
│   ├── theme/                # Tema y estilos globales
│   └── router/               # Navegación y rutas
├── core/
│   ├── network/              # Cliente HTTP (Dio), interceptores
│   ├── error/                # Excepciones y manejo de errores
│   ├── utils/                # Helpers, validadores, constantes
│   └── usecases/             # Base de casos de uso
├── features/                 # Módulos por funcionalidad
│   ├── auth/
│   │   ├── data/
│   │   │   ├── models/
│   │   │   ├── datasources/
│   │   │   └── repositories/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── repositories/
│   │   │   └── usecases/
│   │   └── presentation/
│   │       ├── pages/
│   │       ├── widgets/
│   │       └── blocs/        (o providers, riverpod, etc.)
│   ├── posts/
│   ├── comments/
│   ├── reactions/
│   └── adoption/
├── shared/                   # Widgets y utilidades compartidas
└── l10n/                     # Localización

Cada funcionalidad sigue el mismo patrón: la capa de datos implementa los repositorios definidos en la capa de dominio y consume fuentes de datos remotas que llaman a la API.

## Integración con la API de FastAPI

- La URL base de la API se define en `app/config/app_config.dart` usando variables de entorno.
- Se utiliza **Dio** como cliente HTTP con interceptores para adjuntar tokens JWT y manejar errores de red.
- Las respuestas JSON se mapean a clases modelo usando `json_serializable`.
- La capa de presentación llama a los casos de uso, los cuales orquestan los repositorios y manejan la lógica de negocio.
- El módulo de IA biométrica se integrará más adelante en `features/lost_pets`, subiendo imágenes y consumiendo el endpoint `/api/v1/pets/identify` del backend.

Esta separación mantiene el código móvil mantenible y testeable mientras la API FastAPI se encarga de la lógica de dominio y la similitud vectorial.
