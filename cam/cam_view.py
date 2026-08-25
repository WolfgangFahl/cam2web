"""
Created on 2026-08-25

cam_view - the cam2web shooting and magnifying panel
see https://github.com/WolfgangFahl/cam2web/issues/8
    https://github.com/WolfgangFahl/cam2web/issues/10

@author: wf
"""

import json
import logging
from typing import Tuple

from nicegui import ui

from cam.camera_grid import Grid

BLANK_IMAGE = (
    "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
)


class CamView:
    """
    the panel of one client - the button bar, the picture with its
    stepping triangles, the navigator beside it and the metadata below

    the widgets belong to me, the camera and the live view belong to the
    webserver and are shared by all clients
    """

    # where the stepping triangles sit on the zoom view and what they do
    ARROW_PLACES = {
        "up": ("arrow_drop_up", 0, -1, "top:0;left:50%;transform:translate(-50%,0)"),
        "down": (
            "arrow_drop_down",
            0,
            1,
            "bottom:0;left:50%;transform:translate(-50%,0)",
        ),
        "left": ("arrow_left", -1, 0, "left:0;top:50%;transform:translate(0,-50%)"),
        "right": ("arrow_right", 1, 0, "right:0;top:50%;transform:translate(0,-50%)"),
    }

    # the step grows while an arrow is held - a single sensor pixel is
    # some 0.8 preview pixels and would not be seen at all
    STEP_GROWTH = 1.25
    STEP_MAX = 64.0

    def __init__(self, solution):
        """
        construct me for the given solution

        Args:
            solution: the Cam2WebSolution I am the panel of
        """
        self.solution = solution
        self.webserver = solution.webserver
        self.still_count = 0
        self.live_count = 0
        self.navigator_count = 0
        self.centre_x = 0.5
        self.centre_y = 0.5
        self.dragging = False
        self.step_timer = None
        self.step_size = 1.0

    def setup_ui(self):
        """
        build my panel
        """
        with ui.column().classes("w-full gap-3") as self.container:
            with ui.row().classes("items-center gap-2"):
                self.setup_buttons()
                self.spinner = ui.spinner()
                self.spinner.set_visibility(False)
                self.status = ui.label("idle")
            with ui.row().classes("items-start gap-4"):
                with ui.element("div").style(
                    "position:relative;width:768px;max-width:100%"
                ):
                    # no forced height - the zoom view keeps the aspect
                    # ratio the device serves
                    self.image = ui.image("").style("width:100%")
                    self.setup_arrows()
                self.navigator = ui.interactive_image(
                    BLANK_IMAGE,
                    events=["mousedown", "mousemove", "mouseup"],
                    cross=False,
                    on_mouse=self.on_navigator_mouse,
                ).style("width:256px")
                self.navigator.set_visibility(False)
            self.meta_label = ui.label("").classes("font-mono text-xs")
            self.meta_label.set_visibility(self.webserver.debug)

    def setup_buttons(self):
        """
        the button bar of https://github.com/WolfgangFahl/cam2web/issues/8
        """
        self.shoot_button = ui.button("Shoot", icon="camera", on_click=self.shoot)
        self.live_button = ui.button("Live view", icon="videocam", on_click=self.live)
        self.stop_button = ui.button("Stop", icon="stop", on_click=self.stop)
        self.check_button = ui.button("Check camera", icon="help")
        self.reset_button = ui.button("Reset USB", icon="usb", on_click=self.reset)
        self.rotate_left_button = ui.button(
            icon="rotate_left", on_click=lambda: self.rotate(-90)
        )
        self.rotate_right_button = ui.button(
            icon="rotate_right", on_click=lambda: self.rotate(90)
        )
        options = {level: f"{level}x" for level in self.webserver.ZOOM_LEVELS}
        self.zoom_radio = ui.radio(options, value=1, on_change=self.magnify).props(
            "inline dense"
        )
        for todo in [self.stop_button, self.check_button]:
            todo.disable()

    def setup_arrows(self):
        """
        the stepping triangles at the four edge midpoints of the zoom view -
        they move the magnified area while they are held, starting with a
        single sensor pixel and picking up speed
        """
        self.arrow_buttons = {}
        for name, (icon, dx, dy, place) in self.ARROW_PLACES.items():
            button = (
                ui.button(icon=icon)
                .props("flat dense round color=blue size=lg")
                .style(f"position:absolute;{place};z-index:10")
                .on("mousedown", lambda dx=dx, dy=dy: self.start_stepping(dx, dy))
                .on("mouseup", self.stop_stepping)
                .on("mouseleave", self.stop_stepping)
            )
            button.set_visibility(False)
            self.arrow_buttons[name] = button

    def show_arrows(self, visible: bool):
        """
        show the stepping triangles - they belong to the magnified view
        and have nothing to do in the full one

        Args:
            visible: whether the triangles are shown
        """
        for button in self.arrow_buttons.values():
            button.set_visibility(visible)

    def zoom_level(self) -> int:
        """
        the zoom level the user asked for

        Returns:
            the zoom level - 1 is the full view
        """
        level = int(self.zoom_radio.value)
        return level

    def magnify(self):
        """
        follow the chosen zoom level - magnifying freezes the full view as
        the navigator picture, 1x returns to the full live view while the
        rectangle keeps its place
        """
        magnified = self.zoom_level() > 1
        if magnified and self.live_button.enabled:
            self.live()
        self.retune()
        self.navigator.set_visibility(magnified)
        self.show_arrows(magnified)
        if magnified:
            self.navigator_count += 1
            self.navigator.set_source(f"/api/fullview.jpg?ts={self.navigator_count}")
        self.draw_rectangle()

    def retune(self):
        """
        hand the current zoom, x and y to the running live view and show
        what came back
        """
        meta = self.webserver.zoom(self.zoom_level(), self.centre_x, self.centre_y).body
        self.show_metadata(json.loads(meta))
        self.draw_rectangle()

    def show_metadata(self, meta: dict):
        """
        show the live view metadata below the picture and log it

        Args:
            meta: the metadata as delivered by the zoom call
        """
        text = " ".join(f"{key}={value}" for key, value in meta.items())
        if self.webserver.debug:
            self.meta_label.set_text(text)
        logging.getLogger("cam2web").info(text)

    def box(self) -> Tuple[float, float]:
        """
        the size of the magnified area as a fraction of the full view

        it is the very box the position is computed with, so the rectangle
        and what the camera is asked for can not drift apart

        Returns:
            the box width and height as fractions
        """
        live_view = self.webserver.get_live_view()
        zoom = live_view.grid.zoom
        box = 1.0 / zoom if zoom > 1 else 1.0
        box_x, box_y = live_view.grid.to_display_box(box, box)
        return box_x, box_y

    def draw_rectangle(self):
        """
        draw the white navigation rectangle on the navigator picture
        """
        content = ""
        if self.zoom_level() > 1:
            box_x, box_y = self.box()
            left = max(0.0, min(self.centre_x - box_x / 2, 1.0 - box_x))
            top = max(0.0, min(self.centre_y - box_y / 2, 1.0 - box_y))
            content = (
                f'<rect x="{left*100:.2f}%" y="{top*100:.2f}%" '
                f'width="{box_x*100:.2f}%" height="{box_y*100:.2f}%" '
                'fill="none" stroke="white" stroke-width="2" />'
            )
        self.navigator.set_content(content)

    def navigator_size(self) -> Tuple[float, float]:
        """
        the pixel size of the navigator picture

        Returns:
            the width and height of the frozen full view
        """
        full = self.webserver.full_frame
        size = (1.0, 1.0)
        if full is not None:
            full_grid = Grid.from_jpeg(full)
            size = (float(full_grid.width), float(full_grid.height))
        return size

    def on_navigator_mouse(self, event):
        """
        drag the navigation rectangle - the magnified picture follows
        while the rectangle is moved

        Args:
            event: the mouse event of the navigator picture
        """
        if event.type == "mousedown":
            self.dragging = True
        elif event.type == "mouseup":
            self.dragging = False
        moving = event.type == "mousemove" and self.dragging
        if event.type == "mousedown" or moving:
            width, height = self.navigator_size()
            self.centre_x = max(0.0, min(event.image_x / width, 1.0))
            self.centre_y = max(0.0, min(event.image_y / height, 1.0))
            self.retune()

    def start_stepping(self, dx: int, dy: int):
        """
        step the magnified area while an arrow is held

        Args:
            dx: the horizontal direction - -1, 0 or 1
            dy: the vertical direction - -1, 0 or 1
        """
        self.stop_stepping()
        self.step_size = 1.0
        # half the frame rate - retuning on every frame floods the socket
        # and the browser loses the connection
        interval = 2.0 / max(self.webserver.fps(), 1.0)
        self.step_timer = ui.timer(interval, lambda: self.step(dx, dy))

    def stop_stepping(self):
        """
        stop the stepping started by an arrow
        """
        if self.step_timer is not None:
            self.step_timer.deactivate()
            self.step_timer = None

    def step(self, dx: int, dy: int):
        """
        move the magnified area by the current step - one sensor pixel at
        the first tick, growing while the arrow stays held

        Args:
            dx: the horizontal direction - -1, 0 or 1
            dy: the vertical direction - -1, 0 or 1
        """
        camera = self.webserver.get_camera()
        reference = camera.grid if camera else None
        width = reference.width if reference else 1
        height = reference.height if reference else 1
        size = self.step_size
        self.centre_x = max(0.0, min(self.centre_x + dx * size / width, 1.0))
        self.centre_y = max(0.0, min(self.centre_y + dy * size / height, 1.0))
        self.step_size = min(size * self.STEP_GROWTH, self.STEP_MAX)
        self.retune()

    def live(self):
        """
        show the shared live view stream for this client
        """
        self.live_count += 1
        self.image.set_source(f"/api/liveview.mjpg?ts={self.live_count}")
        self.status.set_text("live view")
        self.live_button.disable()
        self.stop_button.enable()

    def stop(self):
        """
        drop this client's live view - the camera's live view is released
        when the last viewer left

        the image is pointed at a blank picture and the shared live view is
        stopped - a browser keeps the MJPEG connection open even when the
        source is changed so the stream has to end on the server side
        """
        self.image.set_source(BLANK_IMAGE)
        self.webserver.get_live_view().stop()
        self.status.set_text("idle")
        self.stop_button.disable()
        self.live_button.enable()

    def rotate(self, degrees: int):
        """
        turn the served picture by the given degrees

        Args:
            degrees: the clockwise turn to add - 90 or -90
        """
        grid = self.webserver.get_live_view().grid
        grid.rotation = (grid.rotation + degrees) % 360
        self.status.set_text(f"rotation {grid.rotation}")
        self.draw_rectangle()

    def reset(self):
        """
        free the claimed USB device and open the camera anew - the live
        view of all clients ends with it
        """
        self.image.set_source(BLANK_IMAGE)
        self.stop_button.disable()
        self.live_button.enable()
        self.solution.run_busy(
            self.webserver.reset_usb,
            status=self.status,
            button=self.reset_button,
            spinner=self.spinner,
            on_result=self.show_state,
            busy_text="resetting usb ...",
            done_text="usb reset",
            timeout=30.0,
        )

    def show_state(self, state: dict):
        """
        show the camera state in the status label

        Args:
            state: the camera state as delivered by the reset
        """
        present = state.get("present")
        opened = state.get("open")
        self.status.set_text(f"usb reset - present: {present} open: {opened}")

    def shoot(self):
        """
        capture a still for this client and show it - the picture is
        this client's own, not a shared one

        the capture goes through the webserver which switches the live
        view off first, the device serving only one of the two
        """
        if not self.live_button.enabled:
            self.stop()
        self.solution.run_busy(
            self.webserver.capture_still,
            status=self.status,
            button=self.shoot_button,
            spinner=self.spinner,
            on_result=self.show_still,
            busy_text="shooting ...",
            done_text="still",
            timeout=60.0,
        )

    def show_still(self, data: bytes):
        """
        show the given still for this client

        Args:
            data: the JPEG data of the still
        """
        self.still_count += 1
        name = str(self.solution.client.id)
        self.webserver.save_still(name, data)
        self.image.set_source(f"/stills/{name}.jpg?ts={self.still_count}")
