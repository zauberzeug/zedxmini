import logging
from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np
import rosys
from nicegui import run
from pyzed import sl
from rosys.vision import Image, ImageSize


@dataclass
class Frame:
    timestamp: float
    left: Image
    right: Image
    depth: Image
    depth_map: np.ndarray

# rosys.vision.Camera


class Zedxmini:
    def __init__(self) -> None:
        # super().__init__()
        self.name = 'Zedxmini'
        self.log = logging.getLogger(self.name)
        self.log.setLevel(logging.DEBUG)
        self.cam: sl.Camera = None
        self.captured_frames: deque[Frame] = deque(maxlen=30 * 60)

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

    @property
    def has_frames(self) -> bool:
        return len(self.captured_frames) > 0

    @property
    def last_frame(self) -> Frame:
        if not self.has_frames:
            return None
        return self.captured_frames[-1]

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

        last_frame = Frame(timestamp=timestamp, left=left_image, right=right_image,
                           depth=depth_image, depth_map=depth_map.get_data())
        self.captured_frames.append(last_frame)

    def get_depth(self, x, y, size=0, lense_distance_in_mm=7):
        # self.log.info(f'x: {x}, y: {y} with shape: {self.last_frame.depth_map.shape}')
        last_frame = self.captured_frames[-1]
        if size == 0:
            depth_value = last_frame.depth_map[y, x]
        else:
            min_y = int(max(0, y-size))
            max_y = int(min(last_frame.depth_map.shape[0], y+size))
            min_x = int(max(0, x-size))
            max_x = int(min(last_frame.depth_map.shape[1], x+size))
            self.log.info(f'min_y: {min_y}, max_y: {max_y}, min_x: {min_x}, max_x: {max_x}')
            depth_value = np.nanmean(last_frame.depth_map[min_y:max_y, min_x:max_x])
        depth_value -= lense_distance_in_mm
        return depth_value

    def __del__(self):
        self.cam.close()
