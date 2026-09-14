from django.db import migrations


FORWARD_SQL = """
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.oficina_org (
    import_batch_id uuid NOT NULL,
    source_row integer NOT NULL,
    id_oficina text,
    nombre_oficina_origen text
);

CREATE TABLE IF NOT EXISTS staging.priorities_ref (
    import_batch_id uuid NOT NULL,
    source_row integer NOT NULL,
    priority text,
    priority_name text
);

CREATE TABLE IF NOT EXISTS staging.poblacion_cor (
    import_batch_id uuid NOT NULL,
    source_row integer NOT NULL,
    id_punto text,
    ciudad text,
    lat_ref text,
    lon_ref text
);

CREATE TABLE IF NOT EXISTS staging.routes (
    import_batch_id uuid NOT NULL,
    source_row integer NOT NULL,
    id_route text,
    id_oficina_origen text,
    fecha_registro text,
    origin text,
    destination text,
    distance_km text,
    priority text,
    time_window_start text,
    time_window_end text,
    status text,
    created_at text
);

CREATE TABLE IF NOT EXISTS staging.route_payload (
    import_batch_id uuid NOT NULL,
    source_row integer NOT NULL,
    id_route text,
    payload text
);

CREATE TABLE IF NOT EXISTS staging.execution_logs (
    import_batch_id uuid NOT NULL,
    source_row integer NOT NULL,
    id text,
    route_id text,
    execution_time text,
    result text,
    message text
);

CREATE INDEX IF NOT EXISTS stg_routes_batch_idx
    ON staging.routes (import_batch_id);

CREATE INDEX IF NOT EXISTS stg_payload_route_idx
    ON staging.route_payload (import_batch_id, id_route);

CREATE INDEX IF NOT EXISTS stg_logs_route_idx
    ON staging.execution_logs (import_batch_id, route_id, execution_time DESC);
"""

REVERSE_SQL = "DROP SCHEMA IF EXISTS staging CASCADE;"


class Migration(migrations.Migration):
    dependencies = [("logistics", "0001_initial")]

    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]

