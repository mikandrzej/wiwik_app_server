BEGIN TRANSACTION;
DROP TABLE IF EXISTS "devices";
CREATE TABLE IF NOT EXISTS "devices" (
	"device_id"	TEXT NOT NULL UNIQUE,
	"device_type"	TEXT,
	"vehicle_id"	INTEGER,
	"user_id"	INTEGER,
	PRIMARY KEY("device_id")
);
DROP TABLE IF EXISTS "vehicles";
CREATE TABLE IF NOT EXISTS "vehicles" (
	"vehicle_id"	INTEGER NOT NULL UNIQUE,
	"vehicle_name"	TEXT NOT NULL UNIQUE,
	"vehicle_plate"	TEXT,
	PRIMARY KEY("vehicle_id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "measures";
CREATE TABLE IF NOT EXISTS "measures" (
	"measure_id"	INTEGER NOT NULL UNIQUE,
	"measure_timestamp"	INTEGER NOT NULL,
	"measure_type"	TEXT NOT NULL,
	"device_id"	TEXT NOT NULL,
	"measure_value"	REAL NOT NULL,
	FOREIGN KEY("device_id") REFERENCES "devices"("device_id"),
	PRIMARY KEY("measure_id" AUTOINCREMENT)
);
COMMIT;
