import base64
import logging

from fastapi import Response
from fastapi.responses import JSONResponse
from nicegui import app, ui
from rosys.vision.image_route import _process

from zedxmini import StereoCard, Zedxmini, ZedxminiSimulation

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


@app.get('/images/{image_name}')
async def grab_frame(image_name: str, shrink: int = 1) -> Response:
    if camera is None:
        return placeholder
    if camera.last_frame is None:
        return placeholder
    data: bytes | None = None
    if image_name == 'left':
        data = camera.last_frame.left.data
    elif image_name == 'right':
        data = camera.last_frame.right.data
    elif image_name == 'depth':
        data = camera.last_frame.depth.data
    if data is None:
        return placeholder
    data = _process(data, None, shrink, False)
    return Response(content=data, media_type='image/jpeg')


@app.get('/image')
async def grab_image() -> JSONResponse:
    if not camera.has_frames:
        return JSONResponse('')
    assert camera.last_frame is not None
    image = camera.last_frame.left
    assert image is not None
    assert image.data is not None
    encoded_image = base64.b64encode(image.data).decode('utf-8')
    return JSONResponse({
        'camera_id': image.camera_id,
        'width': image.size.width,
        'height': image.size.height,
        'time': image.time,
        'is_broken': image.is_broken,
        'tags': list(image.tags),
        'image': encoded_image,
    })


@app.get('/depth')
async def get_depth(x: int = 0, y: int = 0, size: int = 0) -> Response:
    return Response(str(camera.get_depth(int(x), int(y), size)))


@app.get('/information')
async def get_information() -> JSONResponse:
    return JSONResponse(camera.get_camera_information())

simulation: bool = False
camera: Zedxmini | ZedxminiSimulation
if simulation:
    camera = ZedxminiSimulation()
else:
    camera = Zedxmini()
stereo_card = StereoCard(camera, shrink_factor=3, update_interval=0.1)

ui.run(title='Zedxmini', reload=True, port=80)
