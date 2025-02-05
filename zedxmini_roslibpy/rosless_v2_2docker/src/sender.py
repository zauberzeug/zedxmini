import os
import socket
import struct
import cv2
import numpy as np
import json
from time import sleep, time
import pyzed.sl as sl

# Get configuration from environment
STREAM_PORT = int(os.getenv('STREAM_PORT', '5555'))

def log(msg):
    print(msg, flush=True)

def init_server_socket():
    log("Creating server socket...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    log(f"Binding to port {STREAM_PORT}...")
    server_socket.bind(('0.0.0.0', STREAM_PORT))
    server_socket.listen(5)
    log("Server socket initialized")
    return server_socket

def init_zed_camera():
    log("Initializing ZED camera...")
    zed = sl.Camera()
    
    # Create initialization parameters
    init_params = sl.InitParameters()
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    init_params.camera_resolution = sl.RESOLUTION.HD1080
    init_params.camera_fps = 30
    
    # Open the camera
    status = zed.open(init_params)
    if status != sl.ERROR_CODE.SUCCESS:
        log(f"Failed to open camera: {status}")
        return None
        
    log("Camera initialized successfully")
    return zed

def get_zed_frames(zed):
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        # Get RGB image
        image = sl.Mat()
        zed.retrieve_image(image, sl.VIEW.LEFT)
        rgb_frame = image.get_data()
        
        # Get depth map
        depth = sl.Mat()
        zed.retrieve_measure(depth, sl.MEASURE.DEPTH)
        depth_frame = depth.get_data()
        
        # Get point cloud for center distance
        point_cloud = sl.Mat()
        zed.retrieve_measure(point_cloud, sl.MEASURE.XYZRGBA)
        
        # Get center distance
        x = round(image.get_width() / 2)
        y = round(image.get_height() / 2)
        err, point_cloud_value = point_cloud.get_value(x, y)
        
        distance = None
        if err == sl.ERROR_CODE.SUCCESS and point_cloud_value[2]:
            distance = np.sqrt(point_cloud_value[0] * point_cloud_value[0] +
                             point_cloud_value[1] * point_cloud_value[1] +
                             point_cloud_value[2] * point_cloud_value[2])
        
        # Normalize depth for visualization
        depth_display = (depth_frame * 255.0 / 20000.0).astype(np.uint8)  # 20m max depth
        depth_color = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)
        
        return True, rgb_frame, depth_color, distance
    return False, None, None, None

def send_frame(client, frame, depth_data=None, distance=None):
    try:
        # Compress frame
        _, img_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        data = img_encoded.tobytes()
        
        log(f"Sending RGB frame of size {len(data)}")
        # Send frame size then data
        client.sendall(struct.pack('>L', len(data)))
        client.sendall(data)
        
        # Send depth if available
        if depth_data is not None:
            _, depth_encoded = cv2.imencode('.jpg', depth_data)
            data = depth_encoded.tobytes()
            log(f"Sending depth frame of size {len(data)}")
            client.sendall(struct.pack('>L', len(data)))
            client.sendall(data)
        else:
            log("No depth data available")
            client.sendall(struct.pack('>L', 0))
            
        # Send info if available
        if distance is not None:
            info = json.dumps({
                "center_distance": float(distance),  # Convert to float for JSON
                "timestamp": time()
            }).encode()
            log(f"Sending info of size {len(info)}")
            client.sendall(struct.pack('>L', len(info)))
            client.sendall(info)
        else:
            log("No info available")
            client.sendall(struct.pack('>L', 0))
            
    except (BrokenPipeError, ConnectionResetError) as e:
        log(f"Connection error while sending: {e}")
        return False
    return True

def main():
    log("\n=== Sender Service Starting ===")
    
    # Initialize ZED camera
    zed = init_zed_camera()
    if zed is None:
        log("Failed to initialize camera")
        return
    
    try:
        server_socket = init_server_socket()
        log(f"Server socket listening on port {STREAM_PORT}")
    except Exception as e:
        log(f"Failed to initialize server socket: {e}")
        zed.close()
        return
    
    log("Starting main loop...")
    
    try:
        while True:
            try:
                log("Waiting for client connection...")
                client, addr = server_socket.accept()
                log(f"Client connected from {addr}")
                
                try:
                    while True:
                        # Get frames from ZED
                        ret, rgb, depth, distance = get_zed_frames(zed)
                        if not ret:
                            log("Failed to get frames from camera")
                            sleep(0.1)
                            continue
                        
                        if not send_frame(client, rgb, depth, distance):
                            log("Client disconnected")
                            break
                        
                        sleep(0.01)  # Small delay to prevent CPU overload
                        
                except Exception as e:
                    log(f"Error in client loop: {e}")
                finally:
                    client.close()
                    log("Connection closed")
                    
            except Exception as e:
                log(f"Error in main loop: {e}")
                sleep(1)
    finally:
        zed.close()
        log("Camera closed")

if __name__ == "__main__":
    main() 