-- ---------------------------------------------------------------------------
-- Creates one database per service (the "database-per-service" pattern).
-- Runs automatically on first Postgres startup because it is mounted into
-- /docker-entrypoint-initdb.d/ (see docker-compose.yml).
--
-- In a real deployment each service would typically get its OWN Postgres
-- instance/cluster; we use one instance with three isolated databases here so
-- the whole system runs from a single `docker compose up`.
-- ---------------------------------------------------------------------------

CREATE DATABASE users_db;
CREATE DATABASE products_db;
CREATE DATABASE orders_db;
