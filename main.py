import base64
import logging

from fastapi import Response
from nicegui import app, ui

from zedxmini import StereoCard, Zedxmini

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


camera = Zedxmini()
stereo_card = StereoCard(camera)

ui.run(title='Zedxmini', reload=True, port=80)
