# Solución de la prueba técnica SQL

La solución usa PostgreSQL 16 y consulta los datos originales conservados en el
esquema `staging`. No depende de las tablas operacionales, porque estas contienen
únicamente registros que ya superaron la validación.

## Archivos y orden

1. `001_staging_schema.sql`: crea las seis tablas de datos crudos.
2. `002_reporting_views.sql`: crea conversiones seguras, vistas tipadas, reporte
   consolidado y función parametrizable.
3. `003_sql_test_answers.sql`: contiene las cinco respuestas solicitadas.
4. `004_sql_test_assertions.sql`: valida los resultados dentro de PostgreSQL.
5. `verify_expected_results.py`: calcula controles independientes sobre el Excel.

El importador Django ejecuta la carga al esquema `staging`. Por lo tanto, el
flujo normal es iniciar el proyecto, importar `data/dataset.xlsx` desde la API y
ejecutar los scripts de reporting.

```bash
psql -v ON_ERROR_STOP=1 -d routes_db -f database/001_staging_schema.sql
psql -v ON_ERROR_STOP=1 -d routes_db -f database/002_reporting_views.sql
psql -v ON_ERROR_STOP=1 -d routes_db -f database/004_sql_test_assertions.sql
```

`003_sql_test_answers.sql` contiene consultas de reporte que devuelven miles de
filas. Se recomienda abrirlo y ejecutar cada respuesta por separado durante la
revisión técnica.

Con Docker, los scripts también pueden enviarse directamente al contenedor:

```bash
docker compose exec -T db psql -U routes_user -d routes_db \
  < database/002_reporting_views.sql
docker compose exec -T db psql -U routes_user -d routes_db \
  < database/004_sql_test_assertions.sql
```

## Decisión sobre diferencia de distancia

La consigna solicita una diferencia de distancia, pero no identifica una segunda
distancia explícita. La solución adopta este criterio:

1. calcula con Haversine la distancia entre las coordenadas informadas en el
   payload y las coordenadas de referencia de `poblacion_cor`;
2. presenta el valor como `geographic_distance_km`;
3. calcula `distance_difference_km` como la diferencia absoluta entre
   `routes.distance_km` y esa distancia geográfica.

El cálculo queda en `NULL` cuando las coordenadas faltan, no son numéricas, están
fuera de rango o el punto de referencia no existe. Se usa el radio medio terrestre
de 6.371,0088 km.

## Granularidad del reporte

`reporting.v_route_quality_report` devuelve una fila por ruta y lote de
importación. Cuando una ruta tiene varios logs, muestra el último intento y agrega:

- cantidad total de ejecuciones;
- ejecuciones exitosas;
- ejecuciones con error.

Esto evita multiplicar filas de rutas al unirlas con `execution_logs`.

## Clasificación de calidad

Una ruta queda como `REJECTED` cuando presenta al menos uno de estos indicadores:

- ventana horaria inválida;
- distancia no positiva o no numérica;
- oficina, prioridad, estado o punto inválido;
- payload ausente, duplicado o con JSON inválido;
- coordenadas incompletas, no numéricas o fuera de rango;
- dirección ausente o con formato inválido;
- ciudad de la dirección diferente a la ciudad del punto;
- clave de negocio duplicada.

En caso contrario queda como `VALID`. La columna `quality_reasons` concatena los
motivos aplicables para facilitar auditoría y filtros.

## Filtros reutilizables

La función acepta todos sus parámetros como opcionales:

```sql
SELECT *
FROM reporting.get_route_quality_report(
    p_status => 'READY',
    p_quality_classification => 'REJECTED',
    p_registered_from => '2026-01-01'::timestamp,
    p_registered_to => '2026-01-31 23:59:59'::timestamp
);
```

También se puede consultar directamente la vista y combinar cualquier columna en
una cláusula `WHERE`.

## Controles esperados del dataset

| Control | Resultado |
|---|---:|
| Rutas | 5.000 |
| Ventanas inválidas | 152 |
| Distancias inválidas | 142 |
| Coordenadas inválidas por ruta | 314 |
| Direcciones inválidas | 229 |
| Puntos sin referencia | 135 |
| Ciudad inconsistente | 4.017 |
| Rutas válidas | 658 |
| Rutas rechazadas | 4.342 |
| Logs | 6.434 |
| Rutas con logs | 3.743 |
| Rutas sin logs | 1.257 |

Los controles se reproducen con:

```bash
python database/verify_expected_results.py data/dataset.xlsx
```
