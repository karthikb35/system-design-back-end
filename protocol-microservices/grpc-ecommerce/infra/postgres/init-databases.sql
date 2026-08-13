-- Runs once on first Postgres boot. Creates one database per service so each
-- service owns its schema (database-per-service pattern).
CREATE DATABASE users_db;
CREATE DATABASE products_db;
CREATE DATABASE orders_db;
