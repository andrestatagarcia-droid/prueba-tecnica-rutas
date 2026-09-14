-- Respuesta 1
-- Extraer campos del JSON soportando alias y peso opcional.
SELECT
    import_batch_id,
    source_row,
    route_id,
    point_id,
    address,
    latitude,
    longitude,
    first_piece_weight
FROM reporting.v_route_payload_extracted
ORDER BY import_batch_id, source_row;

-- Respuesta 2
-- Identificar ventanas horarias inválidas o no interpretables.
SELECT
    import_batch_id,
    route_id,
    origin,
    destination,
    time_window_start,
    time_window_end
FROM reporting.v_route_quality_report
WHERE invalid_time_window
ORDER BY import_batch_id, route_id;

-- Respuesta 3
-- Identificar distancias menores o iguales a cero y valores no numéricos.
SELECT
    import_batch_id,
    route_id,
    origin,
    destination,
    distance_km
FROM reporting.v_route_quality_report
WHERE invalid_distance
ORDER BY import_batch_id, route_id;

-- Respuesta 4
-- Relacionar cada ruta con el punto geográfico extraído del payload.
SELECT
    import_batch_id,
    route_id,
    point_id,
    point_city,
    latitude AS reported_latitude,
    longitude AS reported_longitude,
    reference_latitude,
    reference_longitude,
    geographic_distance_km
FROM reporting.v_route_quality_report
ORDER BY import_batch_id, route_id;

-- Respuesta 5
-- Reporte consolidado ejecutable sin filtros.
SELECT *
FROM reporting.get_route_quality_report();

-- Ejemplos de reutilización mediante parámetros posicionales.
-- Solo rutas READY rechazadas de todos los lotes y fechas:
SELECT *
FROM reporting.get_route_quality_report(
    p_status => 'READY',
    p_quality_classification => 'REJECTED'
);

-- Un lote y rango de registro específicos:
-- SELECT *
-- FROM reporting.get_route_quality_report(
--     p_import_batch_id => '00000000-0000-0000-0000-000000000000'::uuid,
--     p_registered_from => '2026-01-01 00:00:00'::timestamp,
--     p_registered_to => '2026-01-31 23:59:59'::timestamp
-- );
