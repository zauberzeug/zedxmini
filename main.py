import rosys
import cv2
import numpy as np
from fastapi import Response
from fastapi.responses import JSONResponse
from nicegui import Client, app, core, ui
from norospy import ROSFoxgloveClient
import base64
import logging
import json
import time

# Configure basic logging - change to WARNING to reduce spam
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Global variables
current_rgb_image = None
current_depth_image = None
current_point_cloud = None
current_imu_data = None
point_cloud_subscription_active = False  # Track subscription state globally
last_point_cloud_time = 0
point_cloud_count = 0
ros_client = None

# Add rate limiting variables
last_rgb_update = 0
last_depth_update = 0
last_imu_update = 0
last_pc_update = 0

def connect_ros():
    global ros_client
    try:
        # Create a new client and start it
        ros_client = ROSFoxgloveClient('ws://localhost:8765')
        ros_client.run_background()
        logger.info("Connected to Foxglove WebSocket server")
        
        # Subscribe to topics
        ros_client.subscribe('/zedxm/zed_node/rgb/image_rect_color', 'sensor_msgs/Image', rgb_image_callback)
        ros_client.subscribe('/zedxm/zed_node/depth/depth_registered', 'sensor_msgs/Image', depth_image_callback)
        ros_client.subscribe('/zedxm/zed_node/imu/data', 'sensor_msgs/Imu', imu_callback)
        ros_client.subscribe(
            '/zedxm/zed_node/point_cloud/cloud_registered',
            'sensor_msgs/PointCloud2',
            point_cloud_callback
        )
        global point_cloud_subscription_active
        point_cloud_subscription_active = True
        
        logger.info("Connected to ROS topics via Foxglove")
    except Exception as e:
        logger.error(f"Failed to connect to Foxglove: {str(e)}")

def imu_callback(message, ts):
    global current_imu_data, last_imu_update
    try:
        # Rate limiting to 10 Hz
        current_time = time.time()
        if current_time - last_imu_update < 0.1:  # 100ms = 10Hz
            return
        last_imu_update = current_time

        # Extract IMU data and timestamps
        receive_time = time.time()
        msg_time = message.header.stamp
        msg_time_sec = msg_time.secs + msg_time.nsecs / 1e9
        
        current_imu_data = {
            'header': {
                'seq': message.header.seq,
                'stamp': {'sec': msg_time.secs, 'nanosec': msg_time.nsecs},
                'frame_id': message.header.frame_id
            },
            'orientation': {
                'x': message.orientation.x,
                'y': message.orientation.y,
                'z': message.orientation.z,
                'w': message.orientation.w
            },
            'angular_velocity': {
                'x': message.angular_velocity.x,
                'y': message.angular_velocity.y,
                'z': message.angular_velocity.z
            },
            'linear_acceleration': {
                'x': message.linear_acceleration.x,
                'y': message.linear_acceleration.y,
                'z': message.linear_acceleration.z
            },
            'receive_timestamp': receive_time,
            'msg_timestamp': msg_time_sec,
            'latency': receive_time - msg_time_sec if msg_time_sec > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error processing IMU data: {str(e)}")

def cleanup_point_cloud():
    global point_cloud_subscription_active, ros_client
    if point_cloud_subscription_active:
        try:
            logger.info("Point cloud subscription will be cleaned up on shutdown")
        except Exception as e:
            logger.error(f"Error cleaning up point cloud subscription: {str(e)}")
    point_cloud_subscription_active = False
    if ros_client:
        try:
            ros_client.close()
            logger.info("ROS client closed")
        except Exception as e:
            logger.error(f"Error closing ROS client: {str(e)}")

@app.on_shutdown
def shutdown():
    cleanup_point_cloud()

def rgb_image_callback(message, ts):
    global current_rgb_image, last_rgb_update
    try:
        # Rate limiting to 5 Hz
        current_time = time.time()
        if current_time - last_rgb_update < 0.2:  # 200ms = 5Hz
            return
        last_rgb_update = current_time

        # Get raw image data
        img_data = np.frombuffer(message.data, dtype=np.uint8)
        
        # Reshape the image data
        height = message.height
        width = message.width
        encoding = message.encoding
        
        if height and width:
            # Reshape based on encoding
            if encoding == 'rgb8':
                img_data = img_data.reshape((height, width, 3))
                img_data = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            elif encoding == 'rgba8':
                img_data = img_data.reshape((height, width, 4))
                img_data = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            elif encoding == 'bgr8':
                img_data = img_data.reshape((height, width, 3))
            elif encoding == 'bgra8':
                img_data = img_data.reshape((height, width, 4))
                img_data = cv2.cvtColor(img_data, cv2.COLOR_BGRA2BGR)
            else:
                logger.warning(f"Unexpected image encoding: {encoding}")
                return
            
            # Resize image to reduce memory usage
            img_data = cv2.resize(img_data, (640, 480))
            
            # Encode as JPEG with compression
            _, buffer = cv2.imencode('.jpg', img_data, [cv2.IMWRITE_JPEG_QUALITY, 85])
            current_rgb_image = buffer.tobytes()
    except Exception as e:
        logger.error(f"Error processing RGB image: {str(e)}")

def depth_image_callback(message, ts):
    global current_depth_image, last_depth_update
    try:
        # Rate limiting to 5 Hz
        current_time = time.time()
        if current_time - last_depth_update < 0.2:  # 200ms = 5Hz
            return
        last_depth_update = current_time

        # Get raw depth data
        depth_data = np.frombuffer(message.data, dtype=np.float32)
        height = message.height
        width = message.width
        
        if height and width:
            # Reshape depth data
            depth_data = depth_data.reshape((height, width))
            
            # Resize to reduce memory usage
            depth_data = cv2.resize(depth_data, (640, 480))
            
            # Handle invalid/infinite values
            depth_data = np.nan_to_num(depth_data, nan=0.0, posinf=20.0, neginf=0.0)
            
            # Normalize depth for visualization
            min_depth = 0.0
            max_depth = 20.0  # 20 meters, adjust based on your needs
            depth_normalized = np.clip(depth_data, min_depth, max_depth)
            depth_range = max_depth - min_depth
            if depth_range > 0:
                depth_normalized = ((depth_normalized - min_depth) / depth_range * 255).astype(np.uint8)
            else:
                depth_normalized = np.zeros_like(depth_normalized, dtype=np.uint8)
            
            # Apply colormap and encode with compression
            depth_colormap = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
            _, buffer = cv2.imencode('.jpg', depth_colormap, [cv2.IMWRITE_JPEG_QUALITY, 85])
            current_depth_image = buffer.tobytes()
    except Exception as e:
        logger.error(f"Error processing depth image: {str(e)}")

def point_cloud_callback(message, ts):
    global current_point_cloud, last_point_cloud_time, point_cloud_count, last_pc_update
    try:
        # Rate limiting to 10 Hz
        current_time = time.time()
        if current_time - last_pc_update < 0.1:  # 100ms = 10Hz
            return
        last_pc_update = current_time

        receive_time = time.time()
        msg_time = message.header.stamp
        msg_time_sec = msg_time.secs + msg_time.nsecs / 1e9
        
        # Calculate time since last message
        time_diff = receive_time - last_point_cloud_time if last_point_cloud_time > 0 else 0
        point_cloud_count += 1
        
        # Extract all relevant metadata
        info = {
            'header': {
                'seq': message.header.seq,
                'stamp': {'sec': msg_time.secs, 'nanosec': msg_time.nsecs},
                'frame_id': message.header.frame_id
            },
            'height': message.height,
            'width': message.width,
            'fields': [{'name': f.name, 'offset': f.offset, 'datatype': f.datatype, 'count': f.count} for f in message.fields],
            'is_bigendian': message.is_bigendian,
            'point_step': message.point_step,
            'row_step': message.row_step,
            'is_dense': message.is_dense,
            'compressed_size': len(message.data),
            'time_since_last': f"{time_diff:.3f}s",
            'message_count': point_cloud_count,
            'average_rate': f"{point_cloud_count / (receive_time - last_point_cloud_time):.2f} Hz" if last_point_cloud_time > 0 else "N/A",
            'receive_timestamp': receive_time,
            'msg_timestamp': msg_time_sec,
            'latency': receive_time - msg_time_sec if msg_time_sec > 0 else 0
        }
        
        # Calculate total points
        if info['point_step'] > 0:
            info['total_points'] = (info['height'] * info['width'])
        
        # Store the info and update timestamp
        current_point_cloud = info
        last_point_cloud_time = receive_time
        
        if point_cloud_count % 10 == 0:  # Log every 10th message
            logger.warning(f"Point cloud rate: {info['average_rate']}, compressed size: {info['compressed_size']/1024/1024:.2f}MB")
            
    except Exception as e:
        logger.error(f"Error processing point cloud: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

@ui.page('/')
def main_page():
    global point_cloud_subscription_active
    
    connect_ros()
    
    with ui.column().classes('w-full items-center'):
        status = ui.label('Connecting to ROS...').classes('text-lg mb-2')
        
        # Create a row for the images
        with ui.row().classes('w-full justify-center gap-4'):
            # Left column - RGB image
            with ui.column().classes('items-center'):
                ui.label('RGB Camera').classes('text-xl mb-2')
                rgb_image = ui.image().classes('w-[640px] h-[480px] border-2')
            
            # Right column - Depth image
            with ui.column().classes('items-center'):
                ui.label('Depth Map').classes('text-xl mb-2')
                depth_image = ui.image().classes('w-[640px] h-[480px] border-2')
        
        def update_images():
            if ros_client is None:
                status.text = 'Not connected to ROS'
                status.classes('text-red-500')
                return
            
            status.text = 'Connected to ROS'
            status.classes('text-green-500')
            
            if current_rgb_image is not None:
                try:
                    rgb_image.source = f'data:image/jpeg;base64,{base64.b64encode(current_rgb_image).decode()}'
                except Exception as e:
                    logger.error(f"Error updating RGB image in UI: {str(e)}")
            
            if current_depth_image is not None:
                try:
                    depth_image.source = f'data:image/jpeg;base64,{base64.b64encode(current_depth_image).decode()}'
                except Exception as e:
                    logger.error(f"Error updating depth image in UI: {str(e)}")
        
        # Add auto-refresh timer with toggle functionality
        timer = ui.timer(0.2, update_images)  # Create timer but don't start it
        timer.active = False  # Initially inactive
        
        def toggle_refresh():
            timer.active = not timer.active  # Toggle timer state
            refresh_button.text = 'Stop Refresh' if timer.active else 'Start Refresh'
            refresh_button.classes('bg-red-500' if timer.active else 'bg-blue-500', remove='bg-red-500 bg-blue-500')
            if not timer.active:  # If stopping, do one final update
                update_images()
        
        # Toggle refresh button
        refresh_button = ui.button('Start Refresh', on_click=toggle_refresh).classes('mt-4 p-2 bg-blue-500 text-white')
        
        # Point cloud status display
        with ui.row().classes('items-center gap-2 mt-4'):
            pc_status = ui.label('Point Cloud: Active').classes('text-green-500')
        
        # Add debug information display
        debug_info = ui.label().classes('mt-4 text-sm font-mono whitespace-pre')
        
        def update_debug():
            debug_info.text = f'''RGB size: {len(current_rgb_image) if current_rgb_image else 0} bytes
Depth size: {len(current_depth_image) if current_depth_image else 0} bytes
Point Cloud size: {current_point_cloud["compressed_size"] if current_point_cloud else 0} bytes'''
        
        # Add debug buttons
        ui.button('Show Image Debug', on_click=update_debug).classes('mt-2 p-2 bg-gray-500 text-white')
        
        def show_point_cloud_debug():
            if current_point_cloud is not None:
                debug_info.text = json.dumps(current_point_cloud, indent=2)
            else:
                debug_info.text = 'No point cloud data received yet'
        
        ui.button('Show Point Cloud Debug', on_click=show_point_cloud_debug).classes('mt-2 p-2 bg-gray-500 text-white')
        
        def show_imu_data():
            if current_imu_data is not None:
                debug_info.text = json.dumps(current_imu_data, indent=2)
            else:
                debug_info.text = 'No IMU data received yet'
        
        ui.button('Show IMU Data', on_click=show_imu_data).classes('mt-2 p-2 bg-gray-500 text-white')

ui.run(title='ZED Mini Camera Viewer', port=8003, reload=True)

