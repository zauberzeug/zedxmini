import os
import socket
import struct
import cv2
import numpy as np
import json
from time import sleep
from flask import Flask, Response, render_template_string
from threading import Thread

# Get configuration from environment
STREAM_HOST = os.getenv('STREAM_HOST', 'localhost')
STREAM_PORT = int(os.getenv('STREAM_PORT', '5555'))
WEB_PORT = int(os.getenv('WEB_PORT', '5001'))

app = Flask(__name__)

# Global frame storage
latest_rgb = None
latest_depth = None
latest_info = None
connection_status = "Not connected"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ZED Camera Streams (Receiver)</title>
    <style>
        .container { display: flex; flex-direction: column; }
        .stream-container { display: flex; }
        .stream { margin: 10px; }
        .info { margin: 10px; padding: 10px; background: #f0f0f0; }
        .status { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="status">Status: {{ status }}</div>
        <div class="stream-container">
            <div class="stream">
                <h2>RGB Stream</h2>
                <img src="{{ url_for('video_feed_rgb') }}" />
            </div>
            <div class="stream">
                <h2>Depth Stream</h2>
                <img src="{{ url_for('video_feed_depth') }}" />
            </div>
        </div>
        <div class="info">
            <h2>Camera Information</h2>
            <pre id="info">{{ info }}</pre>
        </div>
    </div>
</body>
</html>
"""

def receive_frames():
    global latest_rgb, latest_depth, latest_info, connection_status
    
    print(f"Attempting to connect to stream server at {STREAM_HOST}:{STREAM_PORT}")
    
    while True:
        try:
            # Connect to sender
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((STREAM_HOST, STREAM_PORT))
            connection_status = f"Connected to {STREAM_HOST}:{STREAM_PORT}"
            print(connection_status)
            
            while True:
                try:
                    # Receive RGB frame
                    size = struct.unpack('>L', client.recv(4))[0]
                    if size == 0:
                        print("Received empty RGB frame")
                        continue
                    
                    print(f"Receiving RGB frame of size {size}")
                    data = b''
                    while len(data) < size:
                        chunk = client.recv(size - len(data))
                        if not chunk:
                            raise ConnectionError("Connection lost while receiving RGB frame")
                        data += chunk
                    
                    nparr = np.frombuffer(data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        latest_rgb = frame
                        print("RGB frame received successfully")
                    else:
                        print("Failed to decode RGB frame")
                    
                    # Receive depth frame
                    size = struct.unpack('>L', client.recv(4))[0]
                    if size > 0:
                        print(f"Receiving depth frame of size {size}")
                        data = b''
                        while len(data) < size:
                            chunk = client.recv(size - len(data))
                            if not chunk:
                                raise ConnectionError("Connection lost while receiving depth frame")
                            data += chunk
                        
                        nparr = np.frombuffer(data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            latest_depth = frame
                            print("Depth frame received successfully")
                        else:
                            print("Failed to decode depth frame")
                    
                    # Receive info
                    size = struct.unpack('>L', client.recv(4))[0]
                    if size > 0:
                        print(f"Receiving info of size {size}")
                        data = b''
                        while len(data) < size:
                            chunk = client.recv(size - len(data))
                            if not chunk:
                                raise ConnectionError("Connection lost while receiving info")
                            data += chunk
                        latest_info = json.loads(data)
                        print(f"Info received: {latest_info}")
                    
                except (struct.error, ConnectionError) as e:
                    print(f"Stream error: {e}")
                    break
                    
        except Exception as e:
            connection_status = f"Connection error: {e}"
            print(f"{connection_status}, retrying in 1s...")
            sleep(1)
            continue

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, info=latest_info, status=connection_status)

@app.route('/video_feed_rgb')
def video_feed_rgb():
    def generate():
        while True:
            if latest_rgb is not None:
                _, buffer = cv2.imencode('.jpg', latest_rgb)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            sleep(0.01)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_depth')
def video_feed_depth():
    def generate():
        while True:
            if latest_depth is not None:
                _, buffer = cv2.imencode('.jpg', latest_depth)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            sleep(0.01)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

def main():
    # Start frame receiving in a separate thread
    receiver_thread = Thread(target=receive_frames, daemon=True)
    receiver_thread.start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=WEB_PORT)

if __name__ == "__main__":
    main() 