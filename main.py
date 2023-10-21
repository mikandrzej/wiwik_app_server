import time

from flask import Flask, jsonify, request
from flask_mqtt import Mqtt
import sqlite_adapter as db
import json

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = 'iot.2canit.pl'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your server supports TLS, set it True

measures_topic = 'measures/#'

vehicles_topic = 'vehicles/'

mqtt_client = Mqtt(app)


@app.teardown_appcontext
def close_connection(exception):
    db.close_database()


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected successfully')
        mqtt_client.subscribe(measures_topic) # subscribe topic
    else:
        print('Bad connection. Code:', rc)


def handle_mqtt_irvine_measure(device_id, user, measure_type, value):
    print(f"Got irvine measure from user {user} and device_id {device_id}. "
          f"Measure type: {measure_type} with value: {value}")
    timestamp = int(time.time())
    with app.app_context():
        db.insert_measure(timestamp=timestamp, meas_type=measure_type, device_id=device_id, value=value)

    if measure_type == "temperature1":
        # todo get vehicle id based on device id
        veh_id = get_vehicle_id_from_device_id(device_id)
        if veh_id is not None:
            publish_vehicle_irvine_data(timestamp, veh_id, value)


def handle_mqtt_measures_topic(spl_topic, message):
    user = spl_topic[0]
    device_type = spl_topic[1]
    device_id = spl_topic[2]
    measure_type = spl_topic[3]

    if device_type == "irvine":
        handle_mqtt_irvine_measure(device_id, user, measure_type, message)
    else:
        print("Unknown device type " + device_type)


def publish_vehicle_irvine_data(timestamp, vehicle_id, temperature):
    data = {
        "timestamp": timestamp,
        # "vehicle_id": vehicle_id,
        "temperature": float(temperature)
    }
    data_json = json.dumps(data)
    topic = vehicles_topic + str(vehicle_id) + "/irvine"
    mqtt_client.publish(topic, data_json, retain=True)


def get_vehicle_id_from_device_id(device_id):
    with app.app_context():
        vehicle_id = db.select_vehicle_id_from_device_id(device_id)
        return vehicle_id


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    topic = message.topic.split("/")
    root_type = topic[0]
    payload = message.payload.decode()

    if root_type == "measures":
        handle_mqtt_measures_topic(topic[1:], payload)
    else:
        print("Unknown Mqtt root type")


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/api/getVehicles")
def api_get_vehicles():
    vehicles = db.select_vehicles()
    return jsonify(vehicles)


@app.route("/api/getVehicleTempData")
def api_get_vehicle_temp_data():
    args = request.args.to_dict()
    vehicles = args.get("vehicles")
    if vehicles is not None:
        vehicles = vehicles.split(",")
    else:
        vehicles = []

    temperatures = db.select_vehicles_measurements(vehicles=vehicles,
                                    timestamp_from=args.get("dateFrom"),
                                    timestamp_to=args.get("dateTo"),
                                    types=["temperature1"])

    return jsonify(temperatures)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
