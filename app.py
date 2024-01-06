from flask import Flask, render_template, Response, jsonify
from datetime import datetime, timedelta
import time
import websocket
import json
import joblib
import numpy as np
import math
import json
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
kline_data_3m = None
data=None
model_3m = joblib.load('Model_3m.joblib')
def get_nearest_multiple_of_3():
    current_minute = datetime.utcnow().minute
    nearest_multiple = (current_minute // 3) * 3
    return nearest_multiple

def utc_countdown_nearest_multiple_of_3(duration_minutes=3):
    nearest_multiple = get_nearest_multiple_of_3()
    target_time = datetime.utcnow().replace(second=0, microsecond=0, minute=nearest_multiple) + timedelta(minutes=duration_minutes)
    max_duration = datetime.utcnow() + timedelta(minutes=60)
    if duration_minutes > 60:
        duration_minutes = 60
    remaining_time = min(target_time, max_duration) - datetime.utcnow()
    remaining_seconds = int(max(remaining_time.total_seconds(), 0))
    counter_data = {"counter": (remaining_seconds-2)}
    with open('time.json', 'w') as file:
        json.dump(counter_data, file)

@app.route("/stream3m")
def data():
    utc_countdown_nearest_multiple_of_3()
    def Five_Minute_Function():
        symbol = "btcusdt"
        interval = "1m"
        with open('time.json', 'r') as file:
            counter=json.load(file)

        def on_message(ws_app, message):
            global kline_data_3m,data
            data = json.loads(message)
            ws_app.close()
        def on_error(_, error):
            print(f"WebSocket Error: {error}")
        def on_close(_, close_status_code, close_msg):
            print("WebSocket Closed")
        def on_open(ws_app):
            print('WebSocket opened')
        def predict():
            global data
            open_val = float(f"{float(data['k']['o']):.2f}")
            high_val = float(f"{float(data['k']['h']):.2f}")
            low_val = float(f"{float(data['k']['l']):.2f}")
            volume_val = float(f"{float(data['k']['v']):.2f}")
            values = [open_val, high_val, low_val, volume_val]
            arr = [np.array(values)]
            prediction_3m = model_3m.predict(arr)
            kline_data_3m = prediction_3m
            print(kline_data_3m)
            return str(float(kline_data_3m))
        websocket_url = 'wss://stream.binance.com:9443/ws/' + symbol + '@kline_' + interval
        ws_app = websocket.WebSocketApp(websocket_url, on_open=on_open, on_message=on_message, on_error=on_error,
                                       on_close=on_close)
        ws_app.run_forever()
        while counter['counter'] >= 0:
            minutes, seconds = divmod(counter['counter'], 60)
            formatted_time = f"{minutes:02d}:{seconds:02d}"
            counter['time']=formatted_time
            with open('time.json', 'w') as file:
                json.dump(counter, file)  
            if counter['counter'] == 0:
                predict_data = predict()
                print(predict_data)
                with open('output.json', 'w') as file:
                    json.dump(predict_data, file)   
                yield (f"data:{predict_data}-{counter['time']}\n\n")
                counter['counter'] = 180
                with open('time.json','w') as file:
                    json.dump(counter,file)
            else:
                with open('output.json', 'r') as file:
                    prediction = json.load(file)
                yield (f"data:{prediction}-{counter['time']}\n\n")
            time.sleep(1)
            counter['counter']  -= 1
            with open('time.json','w') as file:
                json.dump(counter,file)
    return Response(Five_Minute_Function(), content_type="text/event-stream")

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True,port=5001)
