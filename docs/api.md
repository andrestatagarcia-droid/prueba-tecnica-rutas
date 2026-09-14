# API operacional

Base local: `http://localhost:8000/api/v1`

## Rutas disponibles

| Método | Endpoint | Propósito |
|---|---|---|
| `GET` | `/health/` | Verificar disponibilidad del servicio |
| `POST` | `/routes/import/` | Importar y validar el workbook `.xlsx` |
| `POST` | `/routes/` | Crear una ruta y su payload |
| `GET` | `/routes/` | Listar y filtrar rutas |
| `GET` | `/routes/{id}/` | Consultar el detalle de una ruta |
| `POST` | `/routes/execute/` | Ejecutar hasta 100 rutas seleccionadas |
| `GET` | `/routes/{id}/logs/` | Consultar los intentos de ejecución |

## Crear una ruta

Solo se aceptan los estados iniciales `PENDING` y `READY`. La ruta y su payload
se guardan en una sola transacción.

```json
{
  "origin_office": 1,
  "registered_at": "2026-09-12T08:00:00-05:00",
  "origin": "Centro de distribución Bogotá",
  "destination": "Cliente 100",
  "distance_km": "18.40",
  "priority": 1,
  "time_window_start": "2026-09-12T09:00:00-05:00",
  "time_window_end": "2026-09-12T11:00:00-05:00",
  "status": "READY",
  "payload": {
    "point": 100,
    "address": "Cll 10 # 20-30, Bogotá",
    "latitude": "4.609710",
    "longitude": "-74.081750",
    "first_piece_weight": "8.25",
    "raw_payload": {"source": "manual"}
  }
}
```

La oficina, la prioridad y el punto deben existir en los catálogos. También se
valida distancia positiva, ventana de tiempo, coordenadas, formato de dirección,
coincidencia de ciudad y duplicidad de la clave de negocio.

## Listar y filtrar

Parámetros admitidos:

- `status`: `PENDING`, `READY`, `EXECUTED` o `FAILED`;
- `priority`: identificador de prioridad;
- `origin_office`: identificador de oficina;
- `registered_from` y `registered_to`: fechas ISO 8601;
- `search`: búsqueda en origen, destino y dirección;
- `ordering`: `registered_at`, `created_at`, `distance_km` o `priority`, con `-` para descendente;
- `page` y `page_size`: paginación, con máximo de 100 filas por página.

Ejemplo:

```text
GET /api/v1/routes/?status=READY&priority=1&search=Bogotá&ordering=-distance_km&page_size=50
```

## Ejecutar rutas

```json
{
  "route_ids": [10, 11, 12]
}
```

La operación bloquea las rutas seleccionadas mientras actualiza sus estados.
Solo una ruta en `READY` cambia a `EXECUTED` y produce un log `SUCCESS`. Una
ruta existente en otro estado conserva su estado y produce un log `ERROR`. Un
identificador inexistente se reporta como `NOT_FOUND` y no genera un log huérfano.

Ejemplo de respuesta:

```json
{
  "requested": 3,
  "executed": 1,
  "failed": 2,
  "results": [
    {
      "route_id": 10,
      "result": "SUCCESS",
      "status": "EXECUTED",
      "message": "Ruta ejecutada correctamente."
    },
    {
      "route_id": 11,
      "result": "ERROR",
      "status": "PENDING",
      "message": "La ruta no está en estado READY."
    },
    {
      "route_id": 12,
      "result": "NOT_FOUND",
      "status": null,
      "message": "La ruta no existe."
    }
  ]
}
```
