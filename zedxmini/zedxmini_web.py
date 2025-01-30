import base64

import roslibpy
import rosys

from .zedxmini import ZedxminiBase


class ZedxminiWeb():
    def __init__(self):
        # super().__init__(robot)
        self.ros_client = roslibpy.Ros(host='127.0.0.1', port=9090)

        subscriber = roslibpy.Topic(
            self.ros_client, '/zed/zed_node/rgb/image_rect_color/compressed', 'sensor_msgs/CompressedImage')
        subscriber.subscribe(self.receive_image)

        rosys.on_repeat(self.ros_client.run, 0.1)
        rosys.on_startup(self.test)

    def receive_image(self, msg):
        base64_bytes = msg['data'].encode('ascii')
        image_bytes = base64.b64decode(base64_bytes)
        with open('received-image-{}.{}'.format(msg['header']['seq'], msg['format']), 'wb') as image_file:
            image_file.write(image_bytes)

    async def test(self):
        await rosys.sleep(5)
        print(self.ros_client.get_topics())
