BEGIN;

CREATE TEMP TABLE selected_sql_test_batch ON COMMIT DROP AS
SELECT import_batch_id
FROM staging.routes
GROUP BY import_batch_id
HAVING count(*) = 5000
ORDER BY import_batch_id::text
LIMIT 1;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM selected_sql_test_batch) THEN
        RAISE EXCEPTION 'No existe un lote de staging con 5000 rutas para validar.';
    END IF;
END;
$$;

CREATE TEMP TABLE sql_test_controls (
    control_name text PRIMARY KEY,
    expected_value bigint NOT NULL,
    actual_value bigint NOT NULL
) ON COMMIT DROP;

INSERT INTO sql_test_controls (control_name, expected_value, actual_value)
SELECT 'Rutas', 5000, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
UNION ALL
SELECT 'Ventanas inválidas', 152, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND invalid_time_window
UNION ALL
SELECT 'Distancias inválidas', 142, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND invalid_distance
UNION ALL
SELECT 'Coordenadas inválidas', 314, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND invalid_coordinates
UNION ALL
SELECT 'Direcciones inválidas', 229, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND invalid_address
UNION ALL
SELECT 'Puntos sin referencia', 135, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND unknown_geographic_point
UNION ALL
SELECT 'Ciudades inconsistentes', 4017, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND address_city_mismatch
UNION ALL
SELECT 'Rutas válidas', 658, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND quality_classification = 'VALID'
UNION ALL
SELECT 'Rutas rechazadas', 4342, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND quality_classification = 'REJECTED'
UNION ALL
SELECT 'Logs', 6434, count(*)
FROM reporting.v_execution_logs_typed
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
UNION ALL
SELECT 'Rutas con logs', 3743, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND execution_count > 0
UNION ALL
SELECT 'Rutas sin logs', 1257, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND execution_count = 0
UNION ALL
SELECT 'Distancias geográficas calculables', 4551, count(*)
FROM reporting.v_route_quality_report
WHERE import_batch_id = (SELECT import_batch_id FROM selected_sql_test_batch)
  AND geographic_distance_km IS NOT NULL;

DO $$
DECLARE
    mismatches text;
BEGIN
    SELECT string_agg(
        format('%s: esperado %s, obtenido %s', control_name, expected_value, actual_value),
        E'\n'
        ORDER BY control_name
    )
    INTO mismatches
    FROM sql_test_controls
    WHERE actual_value <> expected_value;

    IF mismatches IS NOT NULL THEN
        RAISE EXCEPTION 'Fallaron controles SQL:%', E'\n' || mismatches;
    END IF;
END;
$$;

SELECT
    control_name,
    expected_value,
    actual_value,
    CASE WHEN expected_value = actual_value THEN 'PASS' ELSE 'FAIL' END AS result
FROM sql_test_controls
ORDER BY control_name;

COMMIT;
