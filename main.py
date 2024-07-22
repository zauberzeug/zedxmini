import logging
import base64
from dataclasses import dataclass

from nicegui import ui, app, run, events
import pyzed.sl as sl
import rosys
from rosys.vision import Image, ImageSize
import cv2
from fastapi import Response
import numpy as np


logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,  # to make sure this config is used
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'DEBUG',
            'stream': 'ext://sys.stdout'
        },
    },
    'loggers': {
        '': {  # this root logger is used for everything without a specific logger
            'handlers': ['console'],
            'level': 'WARN',
            'propagate': False,
        },
        'Zedx2mini': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
})



black_1px = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII='
placeholder = Response(content=base64.b64decode(black_1px.encode('ascii')), media_type='image/png')

@dataclass
class Frame:
    timestamp: float
    left: Image
    right: Image
    depth: Image
    depth_map: np.ndarray


class Zedx2mini:
    def __init__(self) -> None:
        self.name = 'Zedx2mini'
        self.log = logging.getLogger(self.name)
        self.log.setLevel(logging.DEBUG)
        self.cam: sl.Camera = None
        self.last_frame: Frame = None

        rosys.on_startup(self.setup_camera)
        rosys.on_shutdown(self.__del__)
        rosys.on_repeat(self.get_image, 1.0/30.0)

    async def setup_camera(self):
        self.cam = sl.Camera()
        init = sl.InitParameters()
        init.camera_resolution = sl.RESOLUTION.HD1200
        init.camera_fps = 30
        init.depth_mode = sl.DEPTH_MODE.ULTRA
        status = self.cam.open(init)
        self.log.info("Camera Open: %s", status)

    @staticmethod
    def convert(rgba_image: np.ndarray, color=cv2.COLOR_BGRA2BGR) -> bytes:
        rgb_image = cv2.cvtColor(rgba_image, color)
        _, jpeg_image = cv2.imencode('.jpg', rgb_image)
        jpeg_image_bytes = jpeg_image.tobytes()
        return jpeg_image_bytes

    async def get_image(self) -> None:
        if self.cam is None:
            return
        err = await run.io_bound(self.cam.grab)
        if err != sl.ERROR_CODE.SUCCESS:
            self.log.error(err)
            return
        
        timestamp = self.cam.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_milliseconds()
        
        image = sl.Mat()
        self.cam.retrieve_image(image, sl.VIEW.LEFT)
        jpeg_image_bytes = await run.cpu_bound(self.convert, image.get_data())
        left_image = Image(
            camera_id=self.name,
            size=ImageSize(width=image.get_width(), height=image.get_height()),
            time=timestamp,
            data=jpeg_image_bytes,
        )

        image = sl.Mat()
        self.cam.retrieve_image(image, sl.VIEW.RIGHT)
        jpeg_image_bytes = await run.cpu_bound(self.convert, image.get_data())
        right_image = Image(
            camera_id=self.name,
            size=ImageSize(width=image.get_width(), height=image.get_height()),
            time=timestamp,
            data=jpeg_image_bytes,
        )

        image = sl.Mat()
        self.cam.retrieve_image(image, sl.VIEW.DEPTH)
        jpeg_image_bytes = await run.cpu_bound(self.convert, image.get_data())
        depth_image = Image(
            camera_id=self.name,
            size=ImageSize(width=image.get_width(), height=image.get_height()),
            time=timestamp,
            data=jpeg_image_bytes,
        )
        
        depth_map = sl.Mat()
        self.cam.retrieve_measure(depth_map, sl.MEASURE.DEPTH)

        self.last_frame = Frame(timestamp=timestamp, left=left_image, right=right_image, depth=depth_image, depth_map=depth_map.get_data())

    def get_depth(self, x, y, size=15, lense_distance_in_mm=7):
        # self.log.info(f'x: {x}, y: {y} with shape: {self.last_frame.depth_map.shape}')
        min_y = int(max(0, y-size))
        max_y = int(min(self.last_frame.depth_map.shape[0], y+size))
        min_x = int(max(0, x-size))
        max_x = int(min(self.last_frame.depth_map.shape[1], x+size))
        # self.log.info(f'min_y: {min_y}, max_y: {max_y}, min_x: {min_x}, max_x: {max_x}')
        depth_value = np.nanmean(self.last_frame.depth_map[min_y:max_y, min_x:max_x]) - lense_distance_in_mm
        return depth_value


    def __del__(self):
        self.cam.close()


@app.get('/zed/{image_name}')
async def grab_frame(image_name: str) -> Response:
    if camera is None:
        return placeholder
    if camera.last_frame is None:
        return placeholder
    
    if image_name == 'left':
        data = camera.last_frame.left.data
    elif image_name == 'right':
        data = camera.last_frame.right.data
    elif image_name == 'depth':
        data = camera.last_frame.depth.data
    else:
        return placeholder

    if data is None:
        return placeholder
    return Response(content=data, media_type='image/jpeg')


class StereoCard(ui.card):
    def __init__(self, camera: Zedx2mini) -> None:
        super().__init__()
        self.style('position: relative;')
        self.camera = camera

        with self:
            self.label = ui.label('test')
            self.left_image_view = ui.interactive_image('', on_mouse=self.left_mouse_handler, events=['mousedown'], cross=True)
            self.right_image_view = ui.interactive_image('')
            self.depth_image_view = ui.interactive_image('', on_mouse=self.left_mouse_handler, events=['mousedown'], cross=True)
        ui.timer(0.1, self._new_frame)

    def left_mouse_handler(self, e: events.MouseEventArguments) -> None:
        depth = self.camera.get_depth(e.image_x, e.image_y)
        error = abs(depth*0.001)
        rosys.notify(f'Depth: {depth:.3f} +- {error:.3f}')

    def _new_frame(self) -> None:
        if self.camera is None:
            return
        if self.camera.last_frame is None:
            return
        frame = self.camera.last_frame
        self.label.text = f'Image resolution: {frame.left.size.width} x {frame.left.size.height} || Image timestamp: {frame.timestamp}'
        self.left_image_view.set_source(f'/zed/left?{rosys.time()}')
        self.right_image_view.set_source(f'/zed/right?{rosys.time()}')
        self.depth_image_view.set_source(f'/zed/depth?{rosys.time()}')

camera = Zedx2mini()
stereo_card = StereoCard(camera)

ui.run(title='ZedX2Mini', reload=True)
