# Reglas de importación y calidad de datos

## Estructura del archivo

El importador requiere las hojas `oficina_org`, `priorities_ref`, `poblacion_cor`, `routes`, `route_payload` y `execution_logs`, con los encabezados definidos en la prueba.

Un archivo ilegible, una hoja ausente o un encabezado faltante genera un lote con estado `FAILED`. Los errores de contenido producen un lote `COMPLETED` con rutas aceptadas y rechazadas.

## Reglas de ruta

- `idRoute` debe ser un entero positivo y no debe haberse importado antes.
- `idOficinaOrigen` debe existir en `oficina_org`.
- `origin` y `destination` deben contener texto.
- `distance_km` debe ser numérico y mayor que cero.
- `priority` debe ser un entero positivo presente en `priorities_ref`.
- Las fechas deben ser interpretables y `time_window_start` debe ser anterior a `time_window_end`.
- `status` debe ser `PENDING`, `READY`, `EXECUTED` o `FAILED`.
- La combinación de origen, destino y ventana horaria no puede repetirse dentro del archivo ni en la base operacional.

## Reglas del payload

- Debe existir exactamente un payload por ruta.
- El contenido debe ser un objeto JSON válido.
- Se aceptan los alias `direccion` y `address`.
- Se aceptan los alias `latitud`, `latitude` y `lat`.
- Se aceptan los alias `longitud`, `longitude`, `lon` y `lng`.
- La latitud debe estar entre -90 y 90.
- La longitud debe estar entre -180 y 180.
- `idPunto` debe existir en `poblacion_cor`.
- La dirección debe seguir un formato vial básico y terminar con una ciudad.
- La ciudad debe coincidir con la ciudad del punto de referencia.
- Las piezas son opcionales. Si existe un primer peso, debe ser numérico y no negativo.

## Resultado del dataset entregado

| Resultado | Cantidad |
|---|---:|
| Filas evaluadas | 5.000 |
| Rutas válidas | 658 |
| Rutas rechazadas | 4.342 |

| Código de error | Incidencias |
|---|---:|
| `ADDRESS_CITY_MISMATCH` | 4.017 |
| `MISSING_ADDRESS` | 229 |
| `COORDINATE_OUT_OF_RANGE` | 208 |
| `INVALID_TIME_WINDOW` | 152 |
| `NON_POSITIVE_DISTANCE` | 142 |
| `UNKNOWN_GEOGRAPHIC_POINT` | 135 |
| `MISSING_COORDINATE` | 108 |
| `INVALID_COORDINATE` | 102 |

Las incidencias superan el número de rutas rechazadas porque una ruta puede incumplir más de una regla.

## Respuesta del endpoint

`POST /api/v1/routes/import/` devuelve un resumen del lote y como máximo los primeros 200 errores. El listado completo permanece disponible en `import_issues` para consulta posterior.

