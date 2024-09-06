import logging

import rosys
from nicegui import events, ui

try:
    from pyzed import sl
except ModuleNotFoundError:
    logging.warning("ModuleNotFoundError: No module named 'pyzed'")
    sl = None

from .zedxmini import Zedxmini, ZedxminiSimulation


class StereoCard(ui.card):
    def __init__(self, zedxmini: Zedxmini | ZedxminiSimulation, shrink_factor: int = 2, update_interval: float = 1.0 / 30.0, show_crosshair: bool = True) -> None:
        super().__init__()
        self.style('position: relative;')
        self.zedxmini = zedxmini
        self.shrink_factor = shrink_factor
        self.show_crosshair = show_crosshair

        with self:
            self.label = ui.label('test')
            with ui.expansion('Einstellungen').classes('w-full text-align:right'):
                left_image_view_switch = ui.switch('Left Camera', value=True)
                right_image_view_switch = ui.switch('Right Camera', value=False)
                depth_image_view_switch = ui.switch('Depth Image', value=True)
                ui.switch('Show Crosshair').bind_value(self, 'show_crosshair')
                ui.number(label='Shrink', value=shrink_factor, format='%1d').bind_value_to(self, 'shrink_factor')

            if sl is not None:
                with ui.expansion('Camera Control').classes('w-full text-align:right'):
                    with ui.row():
                        ui.label('SATURATION')
                        ui.slider(min=0, max=8, value=self.zedxmini.get_camera_setting(sl.VIDEO_SETTINGS.SATURATION)[0], on_change=lambda e: self.zedxmini.set_camera_setting(
                            sl.VIDEO_SETTINGS.SATURATION, int(e.value)))

            with ui.expansion('Information').classes('w-full text-align:right'):
                ui.label('TODO: zedxmini.get_camera_information()')

            with ui.row():
                with ui.card().tight().bind_visibility_from(left_image_view_switch, 'value'):
                    ui.label('Left Camera')
                    self.left_image_view = ui.interactive_image(
                        '', on_mouse=self.left_mouse_handler, events=['mousedown'], cross=True)
                with ui.card().tight().bind_visibility_from(right_image_view_switch, 'value'):
                    ui.label('Right Camera')
                    self.right_image_view = ui.interactive_image('')
                with ui.card().tight().bind_visibility_from(depth_image_view_switch, 'value'):
                    ui.label('Depth Image')
                    self.depth_image_view = ui.interactive_image(
                        '', on_mouse=self.left_mouse_handler, events=['mousedown'], cross=True)
        ui.timer(update_interval, self._new_frame)

    def left_mouse_handler(self, e: events.MouseEventArguments) -> None:
        point3d = self.zedxmini.get_point(e.image_x, e.image_y)
        rosys.notify(f'Clicked point: {point3d.tuple}')

    def _new_frame(self) -> None:
        if self.zedxmini is None:
            return
        if not self.zedxmini.has_frames:
            return
        frame = self.zedxmini.last_frame
        assert frame is not None
        self.label.text = f'Image resolution: {frame.left.size.width} x {frame.left.size.height} || Image timestamp: {frame.timestamp}'
        self.left_image_view.set_source(f'/images/left?{frame.timestamp}&shrink={int(self.shrink_factor)}')
        self.left_image_view.set_content(
            f'''<circle cx="{(frame.left.size.width/self.shrink_factor)/2}" cy="{(frame.left.size.height/self.shrink_factor)/2}" r="5" stroke="red" stroke-width="3" fill="None" />''' if self.show_crosshair else '')
        self.right_image_view.set_source(f'/images/right?{frame.timestamp}&shrink={int(self.shrink_factor)}')
        self.depth_image_view.set_source(f'/images/depth?{frame.timestamp}&shrink={int(self.shrink_factor)}')
