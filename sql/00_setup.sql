SELECT @@VERSION AS server_version;
GO

IF DB_ID('airline_crm') IS NULL
    CREATE DATABASE airline_crm COLLATE Latin1_General_100_CI_AS_SC_UTF8;
GO

USE airline_crm;
GO

-- four schemas = four zones of the project
IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg');  -- staging: raw text copied from the CSVs
IF SCHEMA_ID('src') IS NULL EXEC('CREATE SCHEMA src');  -- source systems with proper data types
IF SCHEMA_ID('ans') IS NULL EXEC('CREATE SCHEMA ans');  -- answer keys, only for grading
IF SCHEMA_ID('dw')  IS NULL EXEC('CREATE SCHEMA dw');   -- your cleaned, linked tables
GO

SELECT name FROM sys.schemas WHERE name IN ('stg','src','ans','dw');