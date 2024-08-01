from __future__ import annotations

import rosys
from nicegui import events, ui

from .zedxmini import Zedxmini


class StereoCard(ui.card):
    def __init__(self, zedxmini: Zedxmini, update_interval: float = 0.1) -> None:
        super().__init__()
        self.style('position: relative;')
        self.zedxmini = zedxmini

        with self:
            self.label = ui.label('test')
            self.left_image_view = ui.interactive_image(
                '', on_mouse=self.left_mouse_handler, events=['mousedown'], cross=True)
            self.right_image_view = ui.interactive_image('')
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
        self.label.text = f'Image resolution: {frame.left.size.width} x {frame.left.size.height} || Image timestamp: {frame.timestamp}'
        self.left_image_view.set_source(f'/zed/left?{frame.timestamp}')
        self.right_image_view.set_source(f'/zed/right?{frame.timestamp}')
        self.depth_image_view.set_source(f'/zed/depth?{frame.timestamp}')
