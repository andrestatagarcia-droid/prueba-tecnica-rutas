# Colección Postman de la API de rutas

La colección cubre los endpoints operacionales y contiene pruebas automáticas
para respuestas exitosas y reglas de error.

## Archivos

- `Routes-API.postman_collection.json`: colección Postman v2.1;
- `Local.postman_environment.json`: entorno con la URL local;
- `fixtures/archivo-invalido.txt`: archivo del caso negativo de importación;
- `validate_collection.mjs`: verificación estructural sin dependencias externas.

## Preparación

1. Desde la raíz del proyecto, ejecutar `docker compose up --build`.
2. Importar la colección y el entorno en Postman.
3. Seleccionar el entorno **Rutas API - Local**.
4. Abrir la solicitud **Importar dataset válido** y confirmar que el campo
   `file` apunta a `data/dataset.xlsx`. Postman puede solicitar seleccionar el
   archivo manualmente por su política de acceso a archivos locales.
5. Confirmar de la misma manera `postman/fixtures/archivo-invalido.txt` en el
   caso negativo.

## Orden de ejecución

Ejecutar la colección completa y conservar el orden declarado:

1. salud;
2. importación;
3. consulta y captura dinámica de IDs de catálogo;
4. creación de una ruta `READY` única;
5. detalle;
6. ejecución y escenarios negativos;
7. consulta de logs.

La colección captura automáticamente oficina, prioridad, punto geográfico y
ruta creada. Por eso no depende de IDs de catálogo escritos manualmente.

## Cobertura

| Caso | Resultado esperado |
|---|---|
| Servicio disponible | `200` y estado `ok` |
| Workbook válido | `201` y resumen de 5.000 filas |
| Archivo `.txt` | `400` por extensión |
| Listado y filtros | `200` con contrato paginado |
| Ruta válida | `201`, estado `READY` y payload |
| Ventana inválida | `400` |
| Detalle | `200` y ruta encadenada |
| Primera ejecución | `SUCCESS` y estado `EXECUTED` |
| Segunda ejecución | `ERROR` sin cambio de estado |
| ID inexistente | `NOT_FOUND` |
| IDs repetidos | `400` |
| Logs | Incluye intentos `SUCCESS` y `ERROR` |

## Validación estructural

```bash
node postman/validate_collection.mjs
```

Para ejecutar por CLI con Newman, una vez instalado:

```bash
newman run postman/Routes-API.postman_collection.json \
  -e postman/Local.postman_environment.json
```

La ejecución funcional completa requiere que PostgreSQL y Django estén activos.
