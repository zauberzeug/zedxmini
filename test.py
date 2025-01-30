from norospy import ROSFoxgloveClient


def on_image(msg, ts):
    with open(f'/tmp/{ts}.jpg') as f:
        f.write(msg.data)


# Create a new client and start it
client = ROSFoxgloveClient('ws://localhost:8765')
client.run_background()

# Use case 1: Subscribe to data (e.g. images from CARLA, in this example)
client.subscribe('/zed/zed_node/rgb/image_rect_color/compressed', 'sensor_msgs/CompressedImage', on_image)

# Tear down
client.close()
