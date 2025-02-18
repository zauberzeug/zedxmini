import rosys
import cv2
import numpy as np
from fastapi import Response
from fastapi.responses import JSONResponse
from nicegui import Client, app, core, ui
import norospy
from norospy.msg import Image, Imu, CompressedPointCloud2
import base64
import logging
import json
import time

# Configure basic logging - change to WARNING to reduce spam
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Global variables
ros = None
current_rgb_image = None
current_depth_image = None
current_point_cloud = None
current_imu_data = None
point_cloud_topic = None
point_cloud_subscription_active = False  # Track subscription state globally
last_point_cloud_time = 0
point_cloud_count = 0

def connect_ros():
    global ros
    try:
        # Initialize ROS1 connection using norospy
        norospy.init_node('zed_mini_viewer', anonymous=True)
        logger.info("Connected to ROS1")
        
        # Try to set point cloud resolution to reduce data size
        try:
            norospy.set_param('/zed/zed_node/general/pub_resolution', 2)  # HD720 resolution
            norospy.set_param('/zed/zed_node/depth/point_cloud_freq', 5.0)  # 5Hz update rate
            norospy.set_param('/zed/zed_node/point_cloud/cloud_registered/zstd/zstd_encode_level', 1)  # Fastest compression
        except Exception as e:
            logger.warning(f"Could not set point cloud parameters: {e}")
        
        # Subscribe to RGB image topic
        norospy.Subscriber('/zed/zed_node/rgb/image_rect_color', Image, rgb_image_callback)
        
        # Subscribe to depth image topic
        norospy.Subscriber('/zed/zed_node/depth/depth_registered', Image, depth_image_callback)
        
        # Subscribe to IMU topic
        norospy.Subscriber('/zed/zed_node/imu/data', Imu, imu_callback)
        
        # Subscribe to point cloud topic
        norospy.Subscriber(
            '/zed/zed_node/point_cloud/cloud_registered/zstd',
            CompressedPointCloud2,
            point_cloud_callback,
            queue_size=1  # Only keep latest message
        )
        global point_cloud_subscription_active
        point_cloud_subscription_active = True
        
        logger.info("Connected to ROS topics")
    except Exception as e:
        logger.error(f"Failed to connect to ROS: {str(e)}")
        ros = None

def imu_callback(message):
    global current_imu_data
    try:
        # Extract IMU data and timestamps
        receive_time = time.time()
        msg_time = message.header.stamp
        msg_time_sec = msg_time.secs + msg_time.nsecs / 1e9
        
        current_imu_data = {
            'header': {
                'seq': message.header.seq,
                'stamp': {'sec': message.header.stamp.secs, 'nanosec': message.header.stamp.nsecs},
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
    global point_cloud_subscription_active
    if point_cloud_subscription_active:
        try:
            # In norospy, subscribers are automatically cleaned up when the node shuts down
            logger.info("Point cloud subscription will be cleaned up on shutdown")
        except Exception as e:
            logger.error(f"Error cleaning up point cloud subscription: {str(e)}")
    point_cloud_subscription_active = False

@app.on_shutdown
def shutdown():
    cleanup_point_cloud()
    try:
        norospy.signal_shutdown('Application shutting down')
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

def rgb_image_callback(message):
    global current_rgb_image
    try:
        # Get raw image data
        img_data = np.frombuffer(message.data, dtype=np.uint8)
        
        # Reshape the image data
        height = message.height
        width = message.width
        
        if height and width:
            # Reshape assuming RGBA format (4 channels)
            img_data = img_data.reshape((height, width, 4))
            # Convert RGBA to RGB
            img_data = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            
            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', img_data)
            current_rgb_image = buffer.tobytes()
    except Exception as e:
        logger.error(f"Error processing RGB image: {str(e)}")

def depth_image_callback(message):
    global current_depth_image
    try:
        # Get raw depth data
        depth_data = np.frombuffer(message.data, dtype=np.float32)
        
        height = message.height
        width = message.width
        
        if height and width:
            # Reshape depth data
            depth_data = depth_data.reshape((height, width))
            
            # Handle invalid/infinite values
            depth_data = np.nan_to_num(depth_data, nan=0.0, posinf=20.0, neginf=0.0)
            
            # Normalize depth for visualization (adjust min_depth and max_depth as needed)
            min_depth = 0.0
            max_depth = 20.0  # 20 meters, adjust based on your needs
            depth_normalized = np.clip(depth_data, min_depth, max_depth)
            # Ensure we don't divide by zero
            depth_range = max_depth - min_depth
            if depth_range > 0:
                depth_normalized = ((depth_normalized - min_depth) / depth_range * 255).astype(np.uint8)
            else:
                depth_normalized = np.zeros_like(depth_normalized, dtype=np.uint8)
            
            # Apply colormap for better visualization
            depth_colormap = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
            
            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', depth_colormap)
            current_depth_image = buffer.tobytes()
    except Exception as e:
        logger.error(f"Error processing depth image: {str(e)}")

def point_cloud_callback(message):
    global current_point_cloud, last_point_cloud_time, point_cloud_count
    try:
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
                'stamp': {'sec': message.header.stamp.secs, 'nanosec': message.header.stamp.nsecs},
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
    
    if ros is None:
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
            if ros is None or not ros:
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
        
        ui.button('Refresh Images', on_click=update_images).classes('mt-4 p-2 bg-blue-500 text-white')
        
        # Point cloud status display
        with ui.row().classes('items-center gap-2 mt-4'):
            pc_status = ui.label('Point Cloud: Active').classes('text-green-500')
        
        # Add debug information display
        debug_info = ui.label().classes('mt-4 text-sm font-mono whitespace-pre')
        def update_debug():
            rgb_size = len(current_rgb_image) if current_rgb_image is not None else 0
            depth_size = len(current_depth_image) if current_depth_image is not None else 0
            pc_size = current_point_cloud.get('compressed_size', 0) if current_point_cloud else 0
            debug_info.text = (
                f'RGB size: {rgb_size} bytes\n'
                f'Depth size: {depth_size} bytes\n'
                f'Point Cloud size: {pc_size} bytes'
            )
        
        ui.button('Show Image Debug', on_click=update_debug).classes('mt-2 p-2 bg-gray-500 text-white')
        
        # Update point cloud debug display
        point_cloud_info = ui.label().classes('mt-4 text-sm font-mono whitespace-pre-wrap break-all')
        def show_point_cloud_debug():
            if current_point_cloud is not None:
                point_cloud_info.text = (
                    f'Point Cloud Info:\n'
                    f'{json.dumps(current_point_cloud, indent=2)}\n\n'
                    f'Stats:\n'
                    f'- Message count: {point_cloud_count}\n'
                    f'- Compressed size: {current_point_cloud["compressed_size"]/1024/1024:.2f}MB\n'
                    f'- Update rate: {current_point_cloud["average_rate"]}\n'
                    f'- Last update: {current_point_cloud["time_since_last"]}\n'
                    f'Timing:\n'
                    f'- Message timestamp: {time.strftime("%H:%M:%S", time.localtime(current_point_cloud["msg_timestamp"]))}.'
                    f'{int((current_point_cloud["msg_timestamp"] % 1) * 1000):03d}\n'
                    f'- Received timestamp: {time.strftime("%H:%M:%S", time.localtime(current_point_cloud["receive_timestamp"]))}.'
                    f'{int((current_point_cloud["receive_timestamp"] % 1) * 1000):03d}\n'
                    f'- Latency: {current_point_cloud["latency"]*1000:.1f}ms'
                )
            else:
                point_cloud_info.text = 'No point cloud data received yet'
        
        ui.button('Show Point Cloud Debug', on_click=show_point_cloud_debug).classes('mt-2 p-2 bg-gray-500 text-white')
        
        # Add IMU data display
        imu_info = ui.label().classes('mt-4 text-sm font-mono whitespace-pre-wrap break-all')
        def show_imu_data():
            if current_imu_data is not None:
                imu_info.text = (
                    f'IMU Data:\n'
                    f'Orientation (x,y,z,w): {json.dumps(current_imu_data["orientation"], indent=2)}\n'
                    f'Angular Velocity (x,y,z): {json.dumps(current_imu_data["angular_velocity"], indent=2)}\n'
                    f'Linear Acceleration (x,y,z): {json.dumps(current_imu_data["linear_acceleration"], indent=2)}\n\n'
                    f'Timing:\n'
                    f'- Message timestamp: {time.strftime("%H:%M:%S", time.localtime(current_imu_data["msg_timestamp"]))}.'
                    f'{int((current_imu_data["msg_timestamp"] % 1) * 1000):03d}\n'
                    f'- Received timestamp: {time.strftime("%H:%M:%S", time.localtime(current_imu_data["receive_timestamp"]))}.'
                    f'{int((current_imu_data["receive_timestamp"] % 1) * 1000):03d}\n'
                    f'- Latency: {current_imu_data["latency"]*1000:.1f}ms'
                )
            else:
                imu_info.text = 'No IMU data received yet'
        
        ui.button('Show IMU Data', on_click=show_imu_data).classes('mt-2 p-2 bg-gray-500 text-white')

ui.run(title='ZED Mini Camera Viewer', port=8003, reload=True)

