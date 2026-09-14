# Arquitectura del sistema de rutas logísticas

## Objetivo

Construir un MVP que conserve el archivo recibido, identifique errores de calidad y permita operar únicamente con rutas válidas.

## Decisión principal

La solución separa dos capas de datos:

- `staging`: copia sin correcciones de las seis hojas del Excel;
- operacional: rutas validadas, payloads normalizados, ejecuciones e incidencias.

Esta separación evita perder los registros inválidos que se necesitan para la prueba SQL y garantiza que la aplicación no opere sobre información defectuosa.

## Componentes

1. Angular proporciona carga, consulta, filtros, selección y visualización de logs.
2. Django REST Framework expone los contratos HTTP.
3. El servicio de importación carga staging, normaliza nombres JSON y aplica reglas.
4. PostgreSQL conserva tanto la evidencia original como las entidades válidas.

## Límites del MVP

- Arquitectura monolítica modular.
- Importación síncrona para archivos del tamaño entregado.
- Sin autenticación porque no está solicitada.
- Sin microservicios ni mensajería.
- Despliegue en nube únicamente si la versión local queda completa y estable.

## Reglas protegidas en base de datos

- distancia mayor que cero;
- ventana inicial menor que la final;
- coordenadas dentro de los rangos geográficos;
- prioridad positiva;
- combinación exacta de origen, destino y ventana horaria sin duplicados;
- un solo payload normalizado por ruta.

Las validaciones de formato, alias JSON, dirección y pertenencia a catálogos se aplican en el servicio de importación.

## Flujo de importación implementado

1. El API recibe el archivo `.xlsx` y calcula su SHA-256.
2. Se verifican las seis hojas y sus encabezados obligatorios.
3. El contenido original se escribe como texto en el esquema `staging`.
4. Se actualizan los catálogos de oficinas, prioridades y puntos geográficos.
5. Se relacionan `routes` y `route_payload` por `idRoute`.
6. Se normalizan fechas, números, textos y alias JSON.
7. Se registran todos los problemas encontrados por fila.
8. Solo las rutas sin errores se copian a las tablas operacionales.
9. La respuesta devuelve como máximo 200 errores, pero la base conserva la lista completa.

La carga operacional se ejecuta dentro de una transacción. Un fallo técnico revierte las escrituras de staging y de negocio, pero conserva el lote fallido y su mensaje de error.

## Capa de reporting SQL

El esquema `reporting` interpreta los textos de staging mediante conversiones
seguras que devuelven `NULL` ante valores defectuosos, en lugar de interrumpir el
reporte completo. Sus vistas extraen alias JSON, tipan las rutas y referencias,
resumen los logs y producen una fila consolidada por ruta.

La función `reporting.get_route_quality_report` expone filtros opcionales por
lote, estado, clasificación y rango de fecha. Esta capa solo lee staging y no
alimenta las tablas operacionales ni altera los datos recibidos.
