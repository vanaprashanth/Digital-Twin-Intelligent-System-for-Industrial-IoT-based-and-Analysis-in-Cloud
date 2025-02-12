from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from flask_mqtt import Mqtt

cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://esp-iot-controller-default-rtdb.firebaseio.com"
})

app = Flask(__name__)

app.config["MQTT_BROKER_URL"] = "localhost"
app.config["MQTT_BROKER_PORT"] = 1883
app.config["MQTT_USERNAME"] = ""
app.config["MQTT_PASSWORD"] = ""
app.config["MQTT_REFRESH_TIME"] = 1.0  # refresh time in seconds
app.config["MQTT_KEEPALIVE"] = 5  # keep alive time in seconds
app.config["MQTT_TLS_ENABLED"] = False  # Transport Layer Security

CORS(app)
mqtt_client = Mqtt(app)

class Data:
    def __init__(self, id, split_input=False, splitter="", individual_points=""):
        self.id = id
        self.values = []
        self.split_input_value = split_input
        self.splitter = splitter
        self.individual_points = individual_points
    
    def add_value(self, value):
        if not self.split_input_value:
            self.values.append(value)
            db.reference(f"/{self.id}").set(value=self.values)
            if self.get_threshold() != 0 and value.get('value') > self.get_threshold():
                print("Alert")
        else:
            values = value.get("value").split(self.splitter)
            if len(values) != len(self.individual_points.split(",")):
                return
            self.values.append({
                "time": value.get("time"),
                self.individual_points.split(",")[0]: float(values[0]),
                self.individual_points.split(",")[1]: float(values[1]),
                self.individual_points.split(",")[2]: float(values[2]),
                "is_spllited": self.split_input_value,
                "split_label": self.individual_points
            })
            db.reference(f"/{self.id}").set(value=self.values)

    def set_threshold(self, threshold):
        db.reference(f"/threshold/{self.id}").set(value=threshold)

    def get_threshold(self):
        return db.reference(f"/threshold/{self.id}").get() or 0
    
    def to_json(self):
        return db.reference(f"/{self.id}").get() or []
    
    def predict(self):
        if self.split_input_value:
            return {
                "lower_bounds": "Won't work for split data",
                "upper_bounds": "Won't work for split data",
            }
        if len(self.to_json()) < 2:
            return {
                "lower_bounds": "Not enough data",
                "upper_bounds": "Not enough data"
            }
        final_list = [i['value'] for i in self.to_json()]
        l = final_list[-1]
        a = sum(final_list[:len(final_list)]) / len(final_list)
        s = abs(a - l)
        lower_bounds = l - s
        upper_bounds = l + s
        
        return {
            "lower_bounds": lower_bounds,
            "upper_bounds": upper_bounds
        }

temp_data = Data('temp')
humid_data = Data('humid')
pir_data = Data('pir')
accel_data = Data('accel', split_input=True, splitter=",", individual_points="x,y,z")
hall_data = Data('hall')

topic = "/gmu/prashanth/project/topic"

def on_receive_data(type, value):
    if type == 'temp':
        # Date in dd/mm/YY H:M:S format
        temp_data.add_value({
            "value": float(value),
            "time": int(time.time()),
            "is_spllited": temp_data.split_input_value
        })
    elif type == 'humid':
        humid_data.add_value({
            "value": float(value),
            "time": int(time.time()),
            "is_spllited": humid_data.split_input_value
        })
    elif type == 'pir':
        pir_data.add_value({
            "value": int(value),
            "time": int(time.time()),
            "is_spllited": pir_data.split_input_value
        })
    elif type == 'hall':
        hall_data.add_value({
            "value": int(value),
            "time": int(time.time()),
            "is_spllited": hall_data.split_input_value
        })
    elif type == 'accel':
        accel_data.add_value({
            "value": value,
            "time": int(time.time()),
            "is_spllited": accel_data.split_input_value
        })
    else:
        return "error"
    return "ok"

@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
   if rc == 0:
       print('Connected successfully')
       mqtt_client.subscribe(topic, 2) # subscribe topic
   else:
       print('Bad connection. Code:', rc)

@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(
        topic=message.topic,
        payload=message.payload.decode()
    )
    print(data)
    if data.get('topic') == topic:
        # Payload format is type=temp&value=20
        if len(data.get('payload').split('&')) < 2:
            return
        type = data.get('payload').split('&')[0].split('=')[1]
        value = data.get('payload').split('&')[1].split('=')[1]
        res = on_receive_data(type, value)
        if res == "ok":
            mqtt_client.publish(topic+"/return", f"Success", 2)
        else:
            mqtt_client.publish(topic+"/return", "Error", 2)

@app.route("/get_types", methods=['GET'])
def get_types():
    return jsonify({
        "types": [{
            "type": "temp",
            "name": "Temperature"
        }, {
            "type": "humid",
            "name": "Humidity"
        }, {
            "type": "pir",
            "name": "PIR"
        }, {
            "type": "hall",
            "name": "Hall"
        }, {
            "type": "accel",
            "name": "Accelerometer"
        }]
    })

# /post_data?type=temp&value=20
@app.route('/post_data', methods=['GET'])
def api():
    type = request.args.get('type')
    value = request.args.get('value')
    return on_receive_data(type, value)

# /set_threshold?type=temp&value=20
@app.route('/set_threshold', methods=['GET'])
def set_threshold():
    type = request.args.get('type')
    value = request.args.get('value')
    if type == 'temp':
        temp_data.set_threshold(float(value))
    elif type == 'humid':
        humid_data.set_threshold(float(value))
    elif type == 'pir':
        pir_data.set_threshold(float(value))
    elif type == 'hall':
        hall_data.set_threshold(float(value))
    elif type == 'accel':
        accel_data.set_threshold(float(value))
    else:
        return "error"

    print(temp_data.get_threshold())
    print(humid_data.get_threshold())
    return jsonify({
        "temp": temp_data.get_threshold(),
        "humid": humid_data.get_threshold(),
        "pir": pir_data.get_threshold(),
        "hall": hall_data.get_threshold(),
        "accel": accel_data.get_threshold()
    })

@app.route('/get_data', methods=['GET'])
def get_data():
    return jsonify({
        "temp": temp_data.to_json(),
        "humid": humid_data.to_json(),
        "pir": pir_data.to_json(),
        "hall": hall_data.to_json(),
        "accel": accel_data.to_json(),
        "temp_pred": temp_data.predict(),
        "humid_pred": humid_data.predict(),
        "pir_pred": pir_data.predict(),
        "hall_pred": hall_data.predict(),
        "accel_pred": accel_data.predict()
    })

@app.route('/get_threshold', methods=['GET'])
def get_threshold():
    return jsonify({
        "temp": temp_data.get_threshold(),
        "humid": humid_data.get_threshold(),
        "pir": pir_data.get_threshold(),
        "hall": hall_data.get_threshold(),
        "accel": accel_data.get_threshold()
    })

@app.route('/alerts', methods=['GET'])
def alerts():
    temp_alert = False
    humid_alert = False
    pir_alert = False
    hall_alert = False
    accel_alert = False
    if temp_data.get_threshold() != 0 and len(temp_data.values) > 0:
        if temp_data.values[-1].get('value') > temp_data.get_threshold():
            temp_alert = True
    if humid_data.get_threshold() != 0 and len(humid_data.values) > 0:
        if humid_data.values[-1].get('value') > humid_data.get_threshold():
            humid_alert = True
    if pir_data.get_threshold() != 0 and len(pir_data.values) > 0:
        if pir_data.values[-1].get('value') > pir_data.get_threshold():
            pir_alert = True
    if hall_data.get_threshold() != 0 and len(hall_data.values) > 0:
        if hall_data.values[-1].get('value') > hall_data.get_threshold():
            hall_alert = True
    if accel_data.get_threshold() != 0 and len(accel_data.values) > 0:
        if accel_data.values[-1].get('value') > accel_data.get_threshold():
            accel_alert = True
    return jsonify({
        "temp": temp_alert,
        "humid": humid_alert,
        "pir": pir_alert,
        "hall": hall_alert,
        "accel": accel_alert
    })

if __name__ == '__main__':
    app.run(debug=False, port=5001, host="0.0.0.0")