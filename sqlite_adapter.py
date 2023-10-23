import sqlite3
from flask import g
from sqlite3 import Error
import os

DATABASE = 'db\\wiwik_db.db'
DATABASE_INIT_SCRIPT = 'create_db.sql'




def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))


def get_database():
    database = getattr(g, '_database', None)
    if database is None:
        database = connect_database()
        if database is None:
            database = create_database()
    g._database = database
    return database


def connect_database():
    database = None
    try:
        database = sqlite3.connect(DATABASE)
        database.row_factory = make_dicts
    except Error as e:
        print(e)
    return database


def create_database():
    database = None
    db_directory = os.path.dirname(DATABASE)
    if not os.path.exists(db_directory):
        os.makedirs(db_directory)
        print("database folder created")
    try:
        database = sqlite3.connect(DATABASE)
        print(sqlite3.version)
        with open(DATABASE_INIT_SCRIPT, 'r') as sql_file:
            sql_script = sql_file.read()
            database.executescript(sql_script)
            database.commit()
            database.row_factory = make_dicts
    except Error as e:
        print(e)
        if database:
            database.close()
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


def select_devices():
    database = get_database()

    query = "SELECT * FROM devices"
    devices = database.execute(query).fetchall()
    return devices


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

    if result is not None:
        if "vehicle_id" in result:
            return result['vehicle_id']
    return None


def assign_device_to_vehicle(irvine_id, vehicle_id, user_id) -> object:
    result = False
    database = get_database()
    cursor = database.cursor()

    if irvine_id.startswith("irvine"):
        device_type = "irvine"
    else:
        print("Unknown device type: " + irvine_id)
        return False

    query = f"INSERT OR REPLACE INTO devices (device_id, device_type, vehicle_id, user_id) " \
            f'VALUES (?, ?, ?, ?)'
    try:
        cursor.execute(query, [irvine_id, device_type, vehicle_id, user_id])
        result = True
    finally:
        cursor.close()
        database.commit()
    return result
