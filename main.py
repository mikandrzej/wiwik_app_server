import sched
import time

from flask import Flask, jsonify, request
from flask_mqtt import Mqtt
import sqlite_adapter as db
import json
from irvine import IrvineMeasure, IrvineData
from datetime import datetime, timedelta

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = 'iot.2canit.pl'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your server supports TLS, set it True

irvine_topic = 'irvine/#'
vehicles_topic = 'vehicles/'
broker_uptime_topic = "$SYS/broker/uptime"
server_topic = "server/"

mqtt_client = Mqtt(app)


app_start_time = time.time()

@app.teardown_appcontext
def close_connection(exception):
    db.close_database()


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print('MQTT Connected successfully')
        mqtt_client.subscribe(irvine_topic, 2)  # subscribe topic
        mqtt_client.subscribe(broker_uptime_topic)  # subscribe topic
    else:
        print('Bad connection. Code:', rc)


def handle_mqtt_sys_topic(spl_topic, message):
    if spl_topic[0] != "broker":
        return
    if spl_topic[1] != "uptime":
        return

    print("server uptime: " + message)
    uptime = int(time.time() - app_start_time)
    mqtt_client.publish(server_topic + "uptime", uptime)


def handle_mqtt_irvine_topic(spl_topic, message):
    device_id = spl_topic[0]
    measure_type = spl_topic[1]

    if measure_type == "battery":
        json_data = json.loads(message)
        timestamp = json_data["timestamp"]
        value = json_data["battery"]
    elif measure_type == "temperature1":
        json_data = json.loads(message)
        timestamp = json_data["timestamp"]
        value = json_data["temperature1"]
    else:
        print(f"Unknown irvine measure: {measure_type}")
        return

    timestamp = convert_datetime_string_to_since_epoch(timestamp)
    irvine_measure = IrvineMeasure(device_id, measure_type, value, timestamp)

    irvine_data = IrvineData()
    irvine_data.add_measure(irvine_measure)

    #     send to mqtt
    send_irvine_data_to_mqtt(irvine_data)
    # send to database
    send_irvine_data_to_db(irvine_data)


def convert_datetime_string_to_since_epoch(string: str):
    # Parse the offset from the input string
    offset_hours = int(string.split(" GMT")[1])

    # Create a datetime object from the input string
    timestamp = datetime.strptime(string.split(" GMT")[0], "%Y-%m-%d %H:%M:%S")

    # Adjust the datetime object based on the offset
    timestamp = timestamp - timedelta(hours=offset_hours)
    timestamp_epoch = (timestamp - datetime(1970, 1, 1)).total_seconds()

    return timestamp_epoch


def send_irvine_data_to_mqtt(data: IrvineData):
    for measure in data.measures:
        vehicle_id = get_vehicle_id_from_device_id(measure.irvine_id)
        if vehicle_id is None:
            print(f"Irvine ID {measure.irvine_id} not assigned to vehicle")
            continue
        topic = vehicles_topic + str(vehicle_id)
        if measure.meas_type == "temperature1":
            topic = topic + "/irvine_temperature1"
            data = {
                "timestamp": measure.timestamp,
                "value": float(measure.value)
            }
        elif measure.meas_type == "battery":
            topic = topic + "/irvine_battery"
            data = {
                "timestamp": measure.timestamp,
                "value": float(measure.value)
            }
        else:
            print("unknown measure type")
            continue

        data_json = json.dumps(data)
        mqtt_client.publish(topic, data_json, retain=True)


def send_irvine_data_to_db(data: IrvineData):
    for measure in data.measures:
        timestamp = measure.timestamp
        m_type = measure.meas_type
        dev_id = measure.irvine_id
        val = measure.value

    with app.app_context():
        db.insert_measure(timestamp=timestamp, meas_type=m_type, device_id=dev_id, value=val)


def get_vehicle_id_from_device_id(device_id):
    with app.app_context():
        vehicle_id = db.select_vehicle_id_from_device_id(device_id)
        return vehicle_id


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    print("mqtt message: " + message.topic + " "+ message.payload.decode())
    topic = message.topic.split("/")
    root_type = topic[0]
    payload = message.payload.decode()

    if root_type == "irvine":
        handle_mqtt_irvine_topic(topic[1:], payload)
    elif root_type == "$SYS":
        handle_mqtt_sys_topic(topic[1:], payload)
    else:
        print("Unknown Mqtt root type")


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/api/getVehicles")
def api_get_vehicles():
    vehicles = db.select_vehicles()
    return jsonify(vehicles)


@app.route("/api/addVehicle")
def api_add_vehicle():
    args = request.args.to_dict()
    vehicle_name = args.get("veh_name")
    plate_no = args.get("plate_no")
    user_id = args.get("user_id")

    if db.add_vehicle(vehicle_name, plate_no, user_id):
        return "Success", 200
    else:
        return "Commit to db error", 400



@app.route("/api/getVehicleTempData")
def api_get_vehicle_temp_data():
    start_time = time.time() * 1000
    args = request.args.to_dict()
    vehicle_id = args.get("vehicle_id")

    temperatures = db.select_vehicles_measurements(vehicle_id=vehicle_id,
                                                   date=args.get("date"),
                                                   meas_type="temperature1")
    end_time = time.time() * 1000
    print("getVehicleTempData took " + str(end_time - start_time) + "ms")
    return jsonify(temperatures)


@app.route("/api/assignDeviceToVehicle")
def api_assign_device_to_vehicle():
    args = request.args.to_dict()
    device_id = args.get("device_id")
    if device_id is None:
        return "Invalid device_id argument", 400
    vehicle_id = args.get("vehicle_id")
    if vehicle_id is None:
        return "Invalid vehicle_id argument", 400
    user_id = args.get("user_id")
    if user_id is None:
        return "Invalid user_id argument", 400

    if db.assign_device_to_vehicle(device_id, vehicle_id, user_id):
        return "Success", 200
    else:
        return "Commit to db error", 400


@app.route("/api/getDevices")
def api_get_devices():
    devices = db.select_devices()
    return jsonify(devices)


@app.route("/api/getUptime")
def api_get_uptime():
    uptime = int(time.time() - app_start_time)
    return str(uptime), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)