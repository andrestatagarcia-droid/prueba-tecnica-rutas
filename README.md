# Sistema de gestión de rutas logísticas

MVP para importar, validar, consultar y ejecutar rutas logísticas. La solución utiliza Django REST Framework, PostgreSQL y Angular.

## Estado actual

Esta versión contiene:

- configuración base de Django;
- modelos operacionales;
- migraciones operacionales y de staging;
- configuración de PostgreSQL con Docker Compose;
- tablas de staging para conservar los datos originales;
- importación de las seis hojas del workbook;
- normalización de alias JSON y validaciones por fila;
- persistencia exclusiva de rutas válidas;
- registro de errores con fila, campo, código y motivo;
- endpoint `POST /api/v1/routes/import/`;
- creación individual de rutas con payload transaccional;
- listado paginado con filtros, búsqueda y ordenamiento;
- consulta del detalle de una ruta;
- ejecución segura de rutas seleccionadas y registro de cada intento;
- consulta paginada de logs por ruta;
- frontend Angular 22 responsive para importar, filtrar, seleccionar, ejecutar y consultar rutas;
- colección Postman v2.1 con 13 solicitudes y pruebas automáticas;
- solución PostgreSQL para extracción JSON, auditoría y reporte consolidado;
- guía de estudio con las 28 respuestas teóricas, ejemplos aplicados y repreguntas de entrevista;
- auditoría final de requisitos y guion reproducible de demostración local;
- endpoint de salud.

El MVP local y todos los entregables obligatorios están completos. El despliegue cloud permanece como mejora opcional.

## Requisitos

- Docker con Docker Compose.
- Alternativa sin Docker: Python 3.12, PostgreSQL 16, Node.js 24 y npm 11.

## Inicio local

1. Copiar `.env.example` como `.env`.
2. Ejecutar `docker compose up --build`.
3. Verificar `http://localhost:8000/api/v1/health/`.
4. Abrir `http://localhost:4200/`.

Respuesta esperada:

```json
{
  "status": "ok",
  "service": "routes-api"
}
```

## Importar el dataset

Enviar una petición `multipart/form-data`:

```text
POST http://localhost:8000/api/v1/routes/import/
file: dataset.xlsx
```

La respuesta incluye el identificador del lote, registros importados, rechazados, cantidad total de errores y los primeros 200 errores. Todos los errores quedan almacenados en `import_issues`.

## API operacional

Los contratos, filtros y ejemplos de creación y ejecución están documentados en
[`docs/api.md`](docs/api.md).

La colección ejecutable y su orden de uso están documentados en
[`postman/README.md`](postman/README.md).

Las consultas y controles de la prueba SQL están documentados en
[`database/README.md`](database/README.md).

Las 28 respuestas de Python, Django/DRF, arquitectura y Angular están en
[`docs/respuestas_teoricas.pdf`](docs/respuestas_teoricas.pdf).

La revisión requisito por requisito y la presentación local están en
[`docs/auditoria_entrega.pdf`](docs/auditoria_entrega.pdf) y
[`docs/guion_demostracion.pdf`](docs/guion_demostracion.pdf).

La explicación personal de las decisiones del MVP está en
[`docs/bitacora_personal.pdf`](docs/bitacora_personal.pdf).

## Verificación independiente del dataset

El perfilador ejecuta las mismas reglas puras sin requerir Django ni PostgreSQL:

```bash
python backend/scripts/profile_dataset.py data/dataset.xlsx
```

Con la regla estricta de coincidencia entre la ciudad de la dirección y `poblacion_cor`, el resultado esperado es:

```text
5000 filas totales
658 filas válidas
4342 filas rechazadas
```

## Estructura

- `backend`: aplicación Django.
- `data`: dataset entregado para la prueba.
- `database`: staging, vistas de reporting, respuestas SQL y controles independientes.
- `docs`: decisiones de arquitectura.
- `frontend`: aplicación Angular standalone y responsive.
- `postman`: colección, entorno local, fixture y validación estructural.

## Zona horaria

La aplicación usa `America/Bogota`. Django conserva internamente las fechas con soporte de zona horaria y PostgreSQL utiliza `timestamp with time zone`.
