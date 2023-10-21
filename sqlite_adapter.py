import sqlite3
from flask import g

DATABASE = 'db/wiwik_db.db'


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
    return vehicles


def select_vehicles_measurements(vehicles, timestamp_from, timestamp_to, types):
    database = get_database()

    query = "SELECT * FROM measures " \
            "LEFT JOIN devices ON measures.device_id = devices.device_id " \
            "LEFT JOIN vehicles ON devices.vehicle_id = vehicles.vehicle_id"

    filters = []
    if len(vehicles) > 0:
        veh_string = ",".join(vehicles)
        filters.append(f"vehicles.vehicle_id IN ({veh_string})")
    if timestamp_from is not None:
        filters.append(f"measures.measure_timestamp > {timestamp_from}")
    if timestamp_to is not None:
        filters.append(f"measures.measure_timestamp < {timestamp_to}")
    if len(types) > 0:
        types = ["\"" + x + "\"" for x in types]
        meas_type_string = ",".join(types)
        filters.append(f"measures.measure_type IN ({meas_type_string})")

    if len(filters) > 0:
        query += " WHERE "
        query += " AND ".join(filters)

    measurements = database.execute(query).fetchall()
    return measurements


def select_vehicle_id_from_device_id(device_id):
    database = get_database()
    cursor = database.cursor()

    query = f"SELECT devices.vehicle_id FROM devices WHERE devices.device_id IS \"{device_id}\" LIMIT 1"

    result = cursor.execute(query).fetchone()

    if "vehicle_id" in result:
        return result['vehicle_id']
    return None
