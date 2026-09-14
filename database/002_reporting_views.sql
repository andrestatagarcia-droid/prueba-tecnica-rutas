BEGIN;

CREATE SCHEMA IF NOT EXISTS reporting;

CREATE OR REPLACE FUNCTION reporting.try_jsonb(value text)
RETURNS jsonb
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    RETURN value::jsonb;
EXCEPTION
    WHEN invalid_text_representation THEN
        RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION reporting.try_bigint(value text)
RETURNS bigint
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    RETURN NULLIF(btrim(value), '')::bigint;
EXCEPTION
    WHEN invalid_text_representation OR numeric_value_out_of_range THEN
        RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION reporting.try_numeric(value text)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    RETURN NULLIF(btrim(value), '')::numeric;
EXCEPTION
    WHEN invalid_text_representation OR numeric_value_out_of_range THEN
        RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION reporting.try_timestamp(value text)
RETURNS timestamp without time zone
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    RETURN NULLIF(btrim(value), '')::timestamp;
EXCEPTION
    WHEN invalid_datetime_format OR datetime_field_overflow THEN
        RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION reporting.normalize_text(value text)
RETURNS text
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT translate(
        lower(regexp_replace(btrim(value), '[[:space:]]+', ' ', 'g')),
        'áéíóúüñ',
        'aeiouun'
    );
$$;

CREATE OR REPLACE VIEW reporting.v_offices_typed AS
SELECT DISTINCT ON (import_batch_id, reporting.try_bigint(id_oficina))
    import_batch_id,
    reporting.try_bigint(id_oficina) AS office_id,
    NULLIF(btrim(nombre_oficina_origen), '') AS office_name
FROM staging.oficina_org
ORDER BY import_batch_id, reporting.try_bigint(id_oficina), source_row;

CREATE OR REPLACE VIEW reporting.v_priorities_typed AS
SELECT DISTINCT ON (import_batch_id, reporting.try_bigint(priority))
    import_batch_id,
    reporting.try_bigint(priority) AS priority_id,
    NULLIF(btrim(priority_name), '') AS priority_name
FROM staging.priorities_ref
ORDER BY import_batch_id, reporting.try_bigint(priority), source_row;

CREATE OR REPLACE VIEW reporting.v_geographic_points_typed AS
SELECT DISTINCT ON (import_batch_id, reporting.try_bigint(id_punto))
    import_batch_id,
    reporting.try_bigint(id_punto) AS point_id,
    NULLIF(btrim(ciudad), '') AS point_city,
    reporting.try_numeric(lat_ref) AS reference_latitude,
    reporting.try_numeric(lon_ref) AS reference_longitude
FROM staging.poblacion_cor
ORDER BY import_batch_id, reporting.try_bigint(id_punto), source_row;

CREATE OR REPLACE VIEW reporting.v_routes_typed AS
WITH parsed AS (
    SELECT
        import_batch_id,
        source_row,
        reporting.try_bigint(id_route) AS route_id,
        reporting.try_bigint(id_oficina_origen) AS office_id,
        reporting.try_timestamp(fecha_registro) AS registered_at,
        NULLIF(btrim(origin), '') AS origin,
        NULLIF(btrim(destination), '') AS destination,
        reporting.try_numeric(distance_km) AS distance_km,
        reporting.try_bigint(priority) AS priority_id,
        reporting.try_timestamp(time_window_start) AS time_window_start,
        reporting.try_timestamp(time_window_end) AS time_window_end,
        upper(NULLIF(btrim(status), '')) AS status,
        reporting.try_timestamp(created_at) AS created_at
    FROM staging.routes
)
SELECT
    parsed.*,
    count(*) OVER (
        PARTITION BY
            import_batch_id,
            origin,
            destination,
            time_window_start,
            time_window_end
    ) AS route_duplicate_count
FROM parsed;

CREATE OR REPLACE VIEW reporting.v_route_payload_extracted AS
WITH parsed AS (
    SELECT
        import_batch_id,
        source_row,
        reporting.try_bigint(id_route) AS route_id,
        payload AS raw_payload,
        reporting.try_jsonb(payload) AS payload_json
    FROM staging.route_payload
), extracted AS (
    SELECT
        parsed.*,
        COALESCE(
            payload_json ->> 'idPunto',
            payload_json ->> 'id_punto',
            payload_json ->> 'pointId',
            payload_json ->> 'point_id'
        ) AS point_id_text,
        COALESCE(
            payload_json ->> 'direccion',
            payload_json ->> 'dirección',
            payload_json ->> 'address'
        ) AS address_text,
        COALESCE(
            payload_json ->> 'latitud',
            payload_json ->> 'latitude',
            payload_json ->> 'lat'
        ) AS latitude_text,
        COALESCE(
            payload_json ->> 'longitud',
            payload_json ->> 'longitude',
            payload_json ->> 'lon',
            payload_json ->> 'lng'
        ) AS longitude_text,
        COALESCE(
            payload_json #>> '{piezas,0,peso}',
            payload_json #>> '{piezas,0,weight}',
            payload_json #>> '{pieces,0,peso}',
            payload_json #>> '{pieces,0,weight}',
            payload_json #>> '{items,0,peso}',
            payload_json #>> '{items,0,weight}',
            payload_json #>> '{elements,0,peso}',
            payload_json #>> '{elements,0,weight}'
        ) AS first_piece_weight_text
    FROM parsed
)
SELECT
    import_batch_id,
    source_row,
    route_id,
    raw_payload,
    payload_json,
    reporting.try_bigint(point_id_text) AS point_id,
    NULLIF(btrim(address_text), '') AS address,
    reporting.try_numeric(latitude_text) AS latitude,
    reporting.try_numeric(longitude_text) AS longitude,
    reporting.try_numeric(first_piece_weight_text) AS first_piece_weight
FROM extracted;

CREATE OR REPLACE VIEW reporting.v_execution_logs_typed AS
SELECT
    import_batch_id,
    source_row,
    reporting.try_bigint(id) AS execution_log_id,
    reporting.try_bigint(route_id) AS route_id,
    reporting.try_timestamp(execution_time) AS execution_time,
    upper(NULLIF(btrim(result), '')) AS execution_result,
    NULLIF(btrim(message), '') AS execution_message
FROM staging.execution_logs;

CREATE OR REPLACE VIEW reporting.v_route_quality_report AS
WITH route_base AS (
    SELECT *
    FROM reporting.v_routes_typed
), payload_ranked AS (
    SELECT
        payload.*,
        row_number() OVER (
            PARTITION BY import_batch_id, route_id
            ORDER BY source_row
        ) AS payload_position,
        count(*) OVER (
            PARTITION BY import_batch_id, route_id
        ) AS payload_count
    FROM reporting.v_route_payload_extracted AS payload
), log_summary AS (
    SELECT
        import_batch_id,
        route_id,
        count(*) AS execution_count,
        count(*) FILTER (WHERE execution_result = 'SUCCESS') AS success_count,
        count(*) FILTER (WHERE execution_result = 'ERROR') AS error_count
    FROM reporting.v_execution_logs_typed
    GROUP BY import_batch_id, route_id
), latest_log AS (
    SELECT DISTINCT ON (import_batch_id, route_id)
        import_batch_id,
        route_id,
        execution_log_id AS last_execution_log_id,
        execution_time AS last_execution_time,
        execution_result AS last_execution_result,
        execution_message AS last_execution_message
    FROM reporting.v_execution_logs_typed
    ORDER BY import_batch_id, route_id, execution_time DESC NULLS LAST, execution_log_id DESC
), joined AS (
    SELECT
        route.import_batch_id,
        route.source_row AS route_source_row,
        route.route_id,
        route.office_id,
        office.office_name,
        route.registered_at,
        route.origin,
        route.destination,
        route.distance_km,
        route.priority_id,
        priority.priority_name,
        route.time_window_start,
        route.time_window_end,
        route.status,
        route.created_at,
        route.route_duplicate_count,
        payload.payload_count,
        payload.payload_json,
        payload.point_id,
        payload.address,
        payload.latitude,
        payload.longitude,
        payload.first_piece_weight,
        point.point_city,
        point.reference_latitude,
        point.reference_longitude,
        COALESCE(log_summary.execution_count, 0) AS execution_count,
        COALESCE(log_summary.success_count, 0) AS success_count,
        COALESCE(log_summary.error_count, 0) AS error_count,
        latest_log.last_execution_log_id,
        latest_log.last_execution_time,
        latest_log.last_execution_result,
        latest_log.last_execution_message
    FROM route_base AS route
    LEFT JOIN reporting.v_offices_typed AS office
        ON office.import_batch_id = route.import_batch_id
       AND office.office_id = route.office_id
    LEFT JOIN reporting.v_priorities_typed AS priority
        ON priority.import_batch_id = route.import_batch_id
       AND priority.priority_id = route.priority_id
    LEFT JOIN payload_ranked AS payload
        ON payload.import_batch_id = route.import_batch_id
       AND payload.route_id = route.route_id
       AND payload.payload_position = 1
    LEFT JOIN reporting.v_geographic_points_typed AS point
        ON point.import_batch_id = route.import_batch_id
       AND point.point_id = payload.point_id
    LEFT JOIN log_summary
        ON log_summary.import_batch_id = route.import_batch_id
       AND log_summary.route_id = route.route_id
    LEFT JOIN latest_log
        ON latest_log.import_batch_id = route.import_batch_id
       AND latest_log.route_id = route.route_id
), base_flags AS (
    SELECT
        joined.*,
        time_window_start IS NULL
            OR time_window_end IS NULL
            OR time_window_start >= time_window_end AS invalid_time_window,
        distance_km IS NULL OR distance_km <= 0 AS invalid_distance,
        office_id IS NULL OR office_name IS NULL AS unknown_office,
        priority_id IS NULL OR priority_id <= 0 OR priority_name IS NULL AS invalid_priority,
        status IS NULL OR status NOT IN ('PENDING', 'READY', 'EXECUTED', 'FAILED') AS invalid_status,
        payload_count IS NULL OR payload_count <> 1 OR payload_json IS NULL AS invalid_payload,
        point_id IS NULL OR point_city IS NULL AS unknown_geographic_point,
        latitude IS NULL
            OR longitude IS NULL
            OR latitude NOT BETWEEN -90 AND 90
            OR longitude NOT BETWEEN -180 AND 180 AS invalid_coordinates,
        address IS NULL OR address !~* (
            '^(cll|calle|cra|carrera|av|avenida|dg|diagonal|tv|transversal)'
            || '[[:space:]]+[0-9]+[a-z]?[[:space:]]*#[[:space:]]*'
            || '[0-9]+[a-z]?[[:space:]]*-[[:space:]]*[0-9]+'
            || '[[:space:]]*,[[:space:]]*[[:alnum:]áéíóúüñ .-]+$'
        ) AS invalid_address,
        route_duplicate_count > 1 AS exact_duplicate
    FROM joined
), flags AS (
    SELECT
        base_flags.*,
        CASE
            WHEN invalid_address OR unknown_geographic_point THEN false
            ELSE reporting.normalize_text(regexp_replace(address, '^.*,', ''))
                <> reporting.normalize_text(point_city)
        END AS address_city_mismatch
    FROM base_flags
), distances AS (
    SELECT
        flags.*,
        CASE
            WHEN invalid_coordinates
              OR unknown_geographic_point
              OR reference_latitude IS NULL
              OR reference_longitude IS NULL
              OR reference_latitude NOT BETWEEN -90 AND 90
              OR reference_longitude NOT BETWEEN -180 AND 180
            THEN NULL
            ELSE 2 * 6371.0088 * asin(
                LEAST(
                    1.0,
                    sqrt(
                        power(sin(radians((reference_latitude - latitude)::double precision) / 2), 2)
                        + cos(radians(latitude::double precision))
                        * cos(radians(reference_latitude::double precision))
                        * power(sin(radians((reference_longitude - longitude)::double precision) / 2), 2)
                    )
                )
            )
        END AS geographic_distance_km
    FROM flags
)
SELECT
    import_batch_id,
    route_source_row,
    route_id,
    office_id,
    office_name,
    registered_at,
    origin,
    destination,
    distance_km,
    priority_id,
    priority_name,
    time_window_start,
    time_window_end,
    status,
    created_at,
    point_id,
    point_city,
    address,
    latitude,
    longitude,
    reference_latitude,
    reference_longitude,
    first_piece_weight,
    round(geographic_distance_km::numeric, 3) AS geographic_distance_km,
    CASE
        WHEN distance_km IS NULL OR geographic_distance_km IS NULL THEN NULL
        ELSE round(abs(distance_km - geographic_distance_km::numeric), 3)
    END AS distance_difference_km,
    execution_count,
    success_count,
    error_count,
    last_execution_log_id,
    last_execution_time,
    last_execution_result,
    last_execution_message,
    invalid_time_window,
    invalid_distance,
    unknown_office,
    invalid_priority,
    invalid_status,
    invalid_payload,
    unknown_geographic_point,
    invalid_coordinates,
    invalid_address,
    address_city_mismatch,
    exact_duplicate,
    CASE
        WHEN invalid_time_window
          OR invalid_distance
          OR unknown_office
          OR invalid_priority
          OR invalid_status
          OR invalid_payload
          OR unknown_geographic_point
          OR invalid_coordinates
          OR invalid_address
          OR address_city_mismatch
          OR exact_duplicate
        THEN 'REJECTED'
        ELSE 'VALID'
    END AS quality_classification,
    concat_ws(
        '; ',
        CASE WHEN invalid_time_window THEN 'Ventana horaria inválida' END,
        CASE WHEN invalid_distance THEN 'Distancia no positiva o no numérica' END,
        CASE WHEN unknown_office THEN 'Oficina inexistente' END,
        CASE WHEN invalid_priority THEN 'Prioridad inexistente o inválida' END,
        CASE WHEN invalid_status THEN 'Estado fuera del catálogo' END,
        CASE WHEN invalid_payload THEN 'Payload ausente, duplicado o JSON inválido' END,
        CASE WHEN unknown_geographic_point THEN 'Punto geográfico inexistente' END,
        CASE WHEN invalid_coordinates THEN 'Coordenadas incompletas, no numéricas o fuera de rango' END,
        CASE WHEN invalid_address THEN 'Dirección ausente o con formato inválido' END,
        CASE WHEN address_city_mismatch THEN 'Ciudad de la dirección no coincide con el punto' END,
        CASE WHEN exact_duplicate THEN 'Clave de negocio duplicada' END
    ) AS quality_reasons
FROM distances;

CREATE OR REPLACE FUNCTION reporting.get_route_quality_report(
    p_import_batch_id uuid DEFAULT NULL,
    p_status text DEFAULT NULL,
    p_quality_classification text DEFAULT NULL,
    p_registered_from timestamp without time zone DEFAULT NULL,
    p_registered_to timestamp without time zone DEFAULT NULL
)
RETURNS SETOF reporting.v_route_quality_report
LANGUAGE sql
STABLE
AS $$
    SELECT report.*
    FROM reporting.v_route_quality_report AS report
    WHERE (p_import_batch_id IS NULL OR report.import_batch_id = p_import_batch_id)
      AND (p_status IS NULL OR report.status = upper(p_status))
      AND (
          p_quality_classification IS NULL
          OR report.quality_classification = upper(p_quality_classification)
      )
      AND (p_registered_from IS NULL OR report.registered_at >= p_registered_from)
      AND (p_registered_to IS NULL OR report.registered_at <= p_registered_to)
    ORDER BY report.route_id;
$$;

CREATE INDEX IF NOT EXISTS stg_offices_batch_id_idx
    ON staging.oficina_org (import_batch_id, id_oficina);

CREATE INDEX IF NOT EXISTS stg_priorities_batch_id_idx
    ON staging.priorities_ref (import_batch_id, priority);

CREATE INDEX IF NOT EXISTS stg_points_batch_id_idx
    ON staging.poblacion_cor (import_batch_id, id_punto);

COMMIT;
