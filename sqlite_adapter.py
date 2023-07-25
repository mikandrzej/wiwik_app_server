import sqlite3
from flask import g

DATABASE = 'wiwik_db.db'


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))


def get_database():
    database = getattr(g, '_database', None)
    if database is None:
        database = g._database = sqlite3.connect(DATABASE)
        database.row_factory = make_dicts
    return database


def close_database():
    database = getattr(g, '_database', None)
    if database is not None:
        database.close()


def insert_measure(timestamp, meas_type, device_id, value):
    database = get_database()
    cursor = database.cursor()
    # query = f"INSERT INTO measures (measure_timestamp, measure_type, measure_value, device_id) " \
    #         f'VALUES ({timestamp}, "{meas_type}", {value}, "{device_id}")'
    # cursor.execute(query)

    query = f"INSERT INTO measures (measure_timestamp, measure_type, measure_value, device_id) " \
            f'VALUES (?, ?, ?, ?)'
    cursor.execute(query, [timestamp, meas_type, value, device_id])
    cursor.close()

    database.commit()


def select_vehicles():
    database = get_database()

    query = "SELECT * FROM vehicles"
    vehicles = database.execute(query).fetchall()
    print(vehicles)
    return vehicles


def select_vehicles_measurements(vehicles, timestamp_from, timestamp_to):
    database = get_database()

    query = "SELECT * FROM measures LEFT JOIN devices ON measures.device_id = devices.device_id"

    filters = []
    if len(vehicles) > 0:
        veh_string = ",".join(vehicles)
        filters.append(f"vehicle_id IN ({veh_string})")
    if timestamp_from is not None:
        filters.append(f"measure_timestamp > {timestamp_from}")
    if timestamp_to is not None:
        filters.append(f"measure_timestamp > {timestamp_to}")

    if len(filters) > 0:
        query += " WHERE "
        query += " AND ".join(filters)

    measurements = database.execute(query).fetchall()
    print(measurements)
    return measurements
