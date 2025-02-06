#!/usr/bin/env python3
from pathlib import Path
import base64
import json
import time

import cv2
import numpy as np
from nicegui import ui
import roslibpy

import rosys


class RosBridge():
    def __init__(self, websocket_url: str = "ws://localhost:9090") -> None:
        """Initialize ROS bridge with websocket connection.

        Args:
            websocket_url: WebSocket URL for ROS bridge connection (default uses port 9090)
        """
        host = websocket_url.split('://')[1].split(':')[0]
        port = int(websocket_url.split(':')[-1])
        
        self.client = roslibpy.Ros(host=host, port=port)
        self._image_callback = None
        self._connected = False

        # Ensure images directory exists
        self.image_dir = Path('images')
        self.image_dir.mkdir(exist_ok=True)

        rosys.on_repeat(self.connect, 0.1)

    async def connect(self, max_attempts: int = 3, retry_delay: int = 2) -> bool:
        """Connect to ROS bridge websocket server with retries."""
        if self._connected:
            return True

        for attempt in range(max_attempts):
            try:
                self.client.run()
                self._connected = True
                print("Connected to ROS bridge websocket server")
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"Connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                    print(f"Error: {e}")
                else:
                    print("Error: Could not connect to ROS bridge websocket server")
                    print("Please make sure:")
                    print("1. The ZED ROS2 container is running")
                    print("2. The container has network access")
                    print("3. No other service is using the port")
        return False

    def _handle_image(self, message) -> None:
        """Internal handler for image messages."""
        try:
            # Extract timestamp from ROS2 message
            if 'header' in message and 'stamp' in message['header']:
                secs = int(message['header']['stamp']['sec'])
                nsecs = int(message['header']['stamp']['nanosec'])
                ts = secs + nsecs / 1e9
            else:
                ts = time.time()
            
            # Get image data
            encoding = message.get('encoding', 'bgr8')
            height = message['height']
            width = message['width']
            step = message['step']
            
            # Decode image data
            img_data = base64.b64decode(message['data'])
            img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(height, width, 3)

            # Format timestamp string
            timestamp_str = f"{ts:.9f}"
            
            # Save as JPEG
            image_path = self.image_dir / f"{timestamp_str}.jpg"
            is_success, buffer = cv2.imencode('.jpg', img_array)

            if is_success:
                image_path.write_bytes(buffer.tobytes())
                print(f"Saved image at timestamp {timestamp_str}")
            else:
                print("Failed to encode image")

            # Call user callback if set
            if self._image_callback:
                self._image_callback(img_array, float(timestamp_str))

        except Exception as e:
            print(f"Error processing image message: {e}")
            print(f"Message structure: {json.dumps(message, indent=2)}")

    def subscribe_to_images(self, topic: str = '/zedxm/zed_node/rgb/image_rect_color', callback=None) -> None:
        """Subscribe to ZED camera image topic.

        Args:
            topic: ROS topic name (defaults to ZED RGB image topic)
            callback: Optional callback function(image_array, timestamp)
        """
        if not self._connected:
            raise RuntimeError("Not connected to ROS bridge. Call connect() first")

        self._image_callback = callback
        listener = roslibpy.Topic(self.client, topic, 'sensor_msgs/Image')
        listener.subscribe(self._handle_image)
        print(f"Subscribed to image topic: {topic}")

    def close(self) -> None:
        """Close the connection."""
        if self.client:
            self.client.terminate()
        self._connected = False


class FileCounter(ui.label):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0
        rosys.on_repeat(self.count_files, 1)

    def count_files(self) -> None:
        # Count files in images directory
        image_files = len(list(Path('./images').glob('*.jpg')))
        self.count = image_files
        self.text = f"Files: {self.count}"


def on_image(image_array: np.ndarray, timestamp: float) -> None:
    print(f"Received ZED image at {timestamp}")


ros_bridge = RosBridge()


def subscribe_to_images():
    ros_bridge.subscribe_to_images(callback=on_image)


ui.button('Subscribe to ZED camera', on_click=subscribe_to_images)
FileCounter()

ui.run(title='ZED X Mini Camera') 