from __future__ import annotations

import rosys
from nicegui import events, ui

from .zedxmini import Zedxmini, ZedxminiSimulation


class StereoCard(ui.card):
    def __init__(self, zedxmini: Zedxmini | ZedxminiSimulation, shrink_factor: int = 1, update_interval: float = 0.1) -> None:
        super().__init__()
        self.style('position: relative;')
        self.zedxmini = zedxmini
        self.shrink_factor = shrink_factor

        with self:
            self.label = ui.label('test')
            with ui.expansion('Einstellungen').classes('w-full text-align:right'):
                left_image_view_switch = ui.switch('Left Camera', value=True)
                right_image_view_switch = ui.switch('Right Camera', value=False)
                depth_image_view_switch = ui.switch('Depth Image', value=True)
                ui.number(label='Shrink', value=shrink_factor, format='%1d').bind_value_to(self, 'shrink_factor')

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
        depth = self.zedxmini.get_depth(e.image_x, e.image_y)
        error = abs(depth*0.001)
        rosys.notify(f'Depth: {depth:.3f} +- {error:.3f}')

    def _new_frame(self) -> None:
        if self.zedxmini is None:
            return
        if not self.zedxmini.has_frames:
            return
        frame = self.zedxmini.last_frame
        assert frame is not None
        self.label.text = f'Image resolution: {frame.left.size.width} x {frame.left.size.height} || Image timestamp: {frame.timestamp}'
        self.left_image_view.set_source(f'/images/left?{frame.timestamp}&shrink={int(self.shrink_factor)}')
        self.right_image_view.set_source(f'/images/right?{frame.timestamp}&shrink={int(self.shrink_factor)}')
        self.depth_image_view.set_source(f'/images/depth?{frame.timestamp}&shrink={int(self.shrink_factor)}')
