import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import rosys
from nicegui import run
from rosys.geometry import Point3d
from rosys.vision import Image, ImageSize

try:
    from pyzed import sl
except ModuleNotFoundError:
    logging.warning("ModuleNotFoundError: No module named 'pyzed'")
    sl = None


@dataclass
class Frame:
    timestamp: float
    left: Image
    right: Image
    depth: Image
    # TODO
    point_cloud: Any


class ZedxminiBase(ABC):
    name: str

    def __init__(self, name: str) -> None:
        self.name = name
        self.log = logging.getLogger(self.name)
        self.captured_frames: deque[Frame] = deque(maxlen=120)

    @abstractmethod
    def setup_camera(self):
        pass

    @property
    def has_frames(self) -> bool:
        return len(self.captured_frames) > 0

    @property
    def last_frame(self) -> Frame | None:
        if not self.has_frames:
            return None
        return self.captured_frames[-1]

    @abstractmethod
    async def get_image(self) -> None:
        pass

    @abstractmethod
    def get_point(self, x: int, y: int) -> Point3d:
        pass

    @abstractmethod
    def get_camera_information(self) -> dict:
        pass

    @abstractmethod
    def get_camera_setting(self, setting_type) -> tuple[bool, int]:
        pass

    @abstractmethod
    def set_camera_setting(self, setting_type, value) -> int:
        pass


class Zedxmini(ZedxminiBase):
    def __init__(self) -> None:
        super().__init__('Zedxmini')

        self.log.setLevel(logging.DEBUG)
        self.cam: sl.Camera = None

        rosys.on_startup(self.setup_camera)
        rosys.on_shutdown(self.__del__)
        rosys.on_repeat(self.get_image, 1.0/30.0)

    def setup_camera(self):
        self.cam = sl.Camera()
        init = sl.InitParameters()
        init.camera_resolution = sl.RESOLUTION.HD1080
        init.camera_fps = 30
        init.depth_mode = sl.DEPTH_MODE.QUALITY
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

        point_cloud = sl.Mat()
        self.cam.retrieve_measure(point_cloud, sl.MEASURE.XYZ)

        last_frame = Frame(timestamp=timestamp, left=left_image, right=right_image,
                           depth=depth_image, point_cloud=point_cloud)
        self.captured_frames.append(last_frame)

    def get_point(self, x: int, y: int) -> Point3d:
        assert self.has_frames
        assert self.last_frame is not None
        assert self.last_frame.point_cloud is not None
        _, point = self.last_frame.point_cloud.get_value(int(x), int(y))
        return Point3d(x=point[0] / 1000.0, y=point[1] / 1000.0, z=point[2] / 1000.0)

    def get_camera_information(self) -> dict:
        camera_information = self.cam.get_camera_information()
        camera_dict = {
            'camera_model': str(camera_information.camera_model),
            'serial_number': camera_information.serial_number,
            'camera_firmware': camera_information.camera_configuration.firmware_version,
            'sensors_firmware': camera_information.sensors_configuration.firmware_version,
            'resolution': (camera_information.camera_configuration.resolution.width, camera_information.camera_configuration.resolution.height),
            'fps': camera_information.camera_configuration.fps,
            'calibration': {
                'baseline': camera_information.camera_configuration.calibration_parameters.get_camera_baseline(),
                'left_cam': {
                    'fx': camera_information.camera_configuration.calibration_parameters.left_cam.fx,
                    'fy': camera_information.camera_configuration.calibration_parameters.left_cam.fy,
                    'cx': camera_information.camera_configuration.calibration_parameters.left_cam.cx,
                    'cy': camera_information.camera_configuration.calibration_parameters.left_cam.cy,
                    'k1': camera_information.camera_configuration.calibration_parameters.left_cam.disto[0],
                    'k2': camera_information.camera_configuration.calibration_parameters.left_cam.disto[1],
                    'p1': camera_information.camera_configuration.calibration_parameters.left_cam.disto[2],
                    'p2': camera_information.camera_configuration.calibration_parameters.left_cam.disto[3],
                    'k3': camera_information.camera_configuration.calibration_parameters.left_cam.disto[4],
                    'k4': camera_information.camera_configuration.calibration_parameters.left_cam.disto[5],
                    'k5': camera_information.camera_configuration.calibration_parameters.left_cam.disto[6],
                    'k6': camera_information.camera_configuration.calibration_parameters.left_cam.disto[7],
                    's1': camera_information.camera_configuration.calibration_parameters.left_cam.disto[8],
                    's2': camera_information.camera_configuration.calibration_parameters.left_cam.disto[9],
                    's3': camera_information.camera_configuration.calibration_parameters.left_cam.disto[10],
                    's4': camera_information.camera_configuration.calibration_parameters.left_cam.disto[11],
                    'fov_vertical': camera_information.camera_configuration.calibration_parameters.left_cam.v_fov,
                    'fov_horizontal': camera_information.camera_configuration.calibration_parameters.left_cam.h_fov,
                    'fov_diagonal': camera_information.camera_configuration.calibration_parameters.left_cam.d_fov,
                },
                'right_cam': {
                    'fx': camera_information.camera_configuration.calibration_parameters.right_cam.fx,
                    'fy': camera_information.camera_configuration.calibration_parameters.right_cam.fy,
                    'cx': camera_information.camera_configuration.calibration_parameters.right_cam.cx,
                    'cy': camera_information.camera_configuration.calibration_parameters.right_cam.cy,
                    'k1': camera_information.camera_configuration.calibration_parameters.right_cam.disto[0],
                    'k2': camera_information.camera_configuration.calibration_parameters.right_cam.disto[1],
                    'p1': camera_information.camera_configuration.calibration_parameters.right_cam.disto[2],
                    'p2': camera_information.camera_configuration.calibration_parameters.right_cam.disto[3],
                    'k3': camera_information.camera_configuration.calibration_parameters.right_cam.disto[4],
                    'k4': camera_information.camera_configuration.calibration_parameters.right_cam.disto[5],
                    'k5': camera_information.camera_configuration.calibration_parameters.right_cam.disto[6],
                    'k6': camera_information.camera_configuration.calibration_parameters.right_cam.disto[7],
                    's1': camera_information.camera_configuration.calibration_parameters.right_cam.disto[8],
                    's2': camera_information.camera_configuration.calibration_parameters.right_cam.disto[9],
                    's3': camera_information.camera_configuration.calibration_parameters.right_cam.disto[10],
                    's4': camera_information.camera_configuration.calibration_parameters.right_cam.disto[11],
                    'fov_vertical': camera_information.camera_configuration.calibration_parameters.right_cam.v_fov,
                    'fov_horizontal': camera_information.camera_configuration.calibration_parameters.right_cam.h_fov,
                    'fov_diagonal': camera_information.camera_configuration.calibration_parameters.right_cam.d_fov,
                },
            }
        }
        return camera_dict

    def get_camera_setting(self, setting_type) -> tuple[bool, int]:
        if self.cam is None:
            return (False, -1)
        return_value = self.cam.get_camera_settings(setting_type)
        return (return_value == sl.ERROR_CODE.SUCCESS, return_value[1])

    def set_camera_setting(self, setting_type, value) -> bool:
        if self.cam is None:
            return False
        self.cam.set_camera_settings(setting_type, value)
        return False

    def __del__(self):
        self.cam.close()


class ZedxminiSimulation(ZedxminiBase):
    def __init__(self) -> None:
        super().__init__('ZedxminiSimulation')
        rosys.on_repeat(self.get_image, 1.0)

    def setup_camera(self):
        pass

    async def get_image(self) -> None:
        timestamp = rosys.time()
        left_image = Image.create_placeholder(f'{self.name}_left - {timestamp}', timestamp, self.name + "_left")
        right_image = Image.create_placeholder(f'{self.name}_right - {timestamp}', timestamp, self.name + "_right")
        depth_image = Image.create_placeholder(f'{self.name}_depth - {timestamp}', timestamp, self.name + "_depth")

        last_frame = Frame(timestamp=timestamp, left=left_image, right=right_image,
                           depth=depth_image, point_cloud=None)
        self.captured_frames.append(last_frame)

    def get_point(self, x: int, y: int) -> Point3d:
        return Point3d(x=0.0, y=0.0, z=0.3)

    def get_camera_information(self) -> dict:
        return {
            'camera_model': 'Zed Mini',
            'serial_number': '1234567890',
            'camera_firmware': '1.0.0',
            'sensors_firmware': '1.0.0',
            'resolution': (1280, 720),
            'fps': 30,
            'calibration': {
                'baseline': 120,
                'left_cam': {
                    'fx': 700,
                    'fy': 700,
                    'cx': 640,
                    'cy': 360,
                    'k1': 0.0,
                    'k2': 0.0,
                    'p1': 0.0,
                    'p2': 0.0,
                    'k3': 0.0,
                    'k4': 0.0,
                    'k5': 0.0,
                    'k6': 0.0,
                    's1': 0.0,
                    's2': 0.0,
                    's3': 0.0,
                    's4': 0.0,
                    'fov_vertical': 45.0,
                    'fov_horizontal': 90.0,
                    'fov_diagonal': 100.0,
                },
                'right_cam': {
                    'fx': 700,
                    'fy': 700,
                    'cx': 640,
                    'cy': 360,
                    'k1': 0.0,
                    'k2': 0.0,
                    'p1': 0.0,
                    'p2': 0.0,
                    'k3': 0.0,
                    'k4': 0.0,
                    'k5': 0.0,
                    'k6': 0.0,
                    's1': 0.0,
                    's2': 0.0,
                    's3': 0.0,
                    's4': 0.0,
                    'fov_vertical': 45.0,
                    'fov_horizontal': 90.0,
                    'fov_diagonal': 100.0,
                },
            }
        }
