"""
Created on 2026-08-24

@author: wf
"""

import json
import logging
import os
from typing import Optional

from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
    StreamingResponse,
)
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from nicegui import app, ui
from nicegui.client import Client

from cam.camera_grid import Grid
from cam.live_view import BOUNDARY, LiveView
from cam.os_camera import OsCamera
from cam.os_gphoto2 import OsGPhoto2
from cam.version import Version

BLANK_IMAGE = (
    "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
)


class Cam2WebServer(InputWebserver):
    """
    web interface for gphoto2 cams

    webcam emulator server - serves an MJPEG stream and stills
    """

    # zoom levels offered to the user - 5 is served by the device, 10 is
    # that frame magnified twice more by a centred crop
    ZOOM_LEVELS = [1, 5, 10]

    @classmethod
    def get_config(cls) -> WebserverConfig:
        """
        get the configuration for this Webserver
        """
        copy_right = "(c)2026 Wolfgang Fahl"
        config = WebserverConfig(
            copy_right=copy_right,
            version=Version(),
            default_port=8088,
            short_name="cam2web",
            timeout=5.0,
        )
        server_config = WebserverConfig.get(config)
        server_config.solution_class = Cam2WebSolution
        return server_config

    def __init__(self):
        """Constructs all the necessary attributes for the WebServer object."""
        InputWebserver.__init__(self, config=Cam2WebServer.get_config())
        self.camera: Optional[OsCamera] = None
        self.live_view: Optional[LiveView] = None
        self.full_frame: Optional[bytes] = None

        @ui.page("/")
        async def home(client: Client):
            return await self.page(client, Cam2WebSolution.home)

        @app.get("/stills/{name:path}")
        def stills(name: str):
            return self.stills(name)

        @app.get(
            "/api/state.json",
            response_class=JSONResponse,
            summary="camera and server state",
            description="whether a camera is present and open, its size and "
            "rotation, the configured frames per second and the number of "
            "viewers",
        )
        def state() -> JSONResponse:
            """
            the camera and server state
            """
            return self.state()

        @app.get(
            "/api/summary.txt",
            response_class=PlainTextResponse,
            summary="gphoto2 device summary",
            description="the raw gphoto2 summary of the attached camera as "
            "plain text - locale dependent and some 4 KB, a diagnostic path "
            "and not one to poll",
        )
        def summary() -> PlainTextResponse:
            """
            the gphoto2 device summary
            """
            return self.summary()

        @app.get(
            "/api/still.jpg",
            response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}}},
            summary="capture a still",
            description="release the shutter and serve the captured picture at "
            "full resolution as JPEG",
        )
        def still() -> Response:
            """
            a still captured at full resolution
            """
            return self.still()

        @app.get(
            "/api/liveview.jpg",
            response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}}},
            summary="one live view frame",
            description="a single frame of the live view as JPEG - the live "
            "view is started when it is not running yet and serves whatever "
            "the running view is tuned to; the tuning is done with /api/zoom",
        )
        def liveview_jpg() -> Response:
            """
            one frame of the live view
            """
            return self.liveview_jpg()

        @app.get(
            "/api/liveview.mjpg",
            response_class=StreamingResponse,
            responses={200: {"content": {"multipart/x-mixed-replace": {}}}},
            summary="continuous live view",
            description="the live view as an MJPEG stream at the configured "
            "frames per second - the camera's live view is released when the "
            "last viewer left; the stream carries no zoom parameters so that "
            "it stays open while the view is retuned with /api/zoom",
        )
        def liveview_mjpg() -> StreamingResponse:
            """
            the continuous live view
            """
            return self.liveview_mjpg()

        @app.get(
            "/api/zoom",
            response_class=JSONResponse,
            summary="retune the running live view",
            description="magnify the running live view without reopening it - "
            "zoom 1 is the full view, x and y are the centre of the magnified "
            "area in 0..1 of the picture as the user sees it, rotation "
            "included; the resulting live view metadata is returned",
        )
        def zoom(zoom: int = 1, x: float = 0.5, y: float = 0.5) -> JSONResponse:
            """
            retune the running live view
            """
            return self.zoom(zoom, x, y)

        @app.get(
            "/api/live.json",
            response_class=JSONResponse,
            summary="live view metadata",
            description="what the live view is doing right now - zoom, device "
            "and digital share, rotation, the sensor centre, the position sent "
            "to the device, the frame size and the measured frame rate",
        )
        def live_json() -> JSONResponse:
            """
            the live view metadata
            """
            return JSONResponse(content=self.get_live_view().metadata())

        @app.get(
            "/api/fullview.jpg",
            response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}}},
            summary="the full view the magnification navigates in",
            description="the last full view frame taken before the live view "
            "was magnified - the device serves one view at a time so the "
            "navigator picture is a frozen one",
        )
        def fullview() -> Response:
            """
            the frozen full view
            """
            return self.fullview()

    def get_camera(self) -> Optional[OsCamera]:
        """
        my camera, created from the attached device on first use

        Returns:
            the camera or None when no device is attached
        """
        if self.camera is None:
            self.camera = OsCamera.instance(base_path=self.base_path())
        return self.camera

    def base_path(self) -> Optional[str]:
        """
        the base path for the reference pictures

        Returns:
            the configured base path or None
        """
        base_path = self.config.base_path
        return base_path

    def fps(self) -> float:
        """
        the configured maximum frames per second

        Returns:
            the frames per second
        """
        fps = getattr(getattr(self, "args", None), "fps", 20.0)
        return fps

    def rotation(self) -> int:
        """
        the configured clockwise display rotation

        Returns:
            the rotation in degrees - 0 for the EXIF based auto mode
        """
        rotate = getattr(getattr(self, "args", None), "rotate", "0")
        rotation = 0 if rotate == "auto" else int(rotate)
        return rotation

    def summary(self) -> PlainTextResponse:
        """
        the gphoto2 summary of the camera

        Returns:
            PlainTextResponse: the summary text
        """
        camera = self.get_camera()
        response = PlainTextResponse(content=camera.summary())
        return response

    def still_path(self, name: str) -> str:
        """
        the path of the still with the given name

        Args:
            name: the name of the still

        Returns:
            the path of the still
        """
        path = os.path.join(self.config.base_path, "stills", f"{name}.jpg")
        return path

    def save_still(self, name: str, data: bytes) -> str:
        """
        save the given still data under the given name

        Args:
            name: the name of the still
            data: the JPEG data of the still

        Returns:
            the path the still was saved to
        """
        path = self.still_path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as jpeg_file:
            jpeg_file.write(data)
        return path

    def stills(self, name: str) -> Response:
        """
        serve the still with the given name

        Args:
            name: the name of the still

        Returns:
            Response: the JPEG file or a 404
        """
        path = self.still_path(name.removesuffix(".jpg"))
        if os.path.isfile(path):
            response = FileResponse(path, media_type="image/jpeg")
        else:
            response = Response(content="no such still", status_code=404)
        return response

    def still(self) -> Response:
        """
        a still captured at full resolution

        Returns:
            Response: the JPEG data of the still
        """
        camera = self.get_camera()
        data = self.get_live_view().grid.rotate(camera.capture_still())
        response = Response(content=data, media_type="image/jpeg")
        return response

    def get_live_view(self) -> LiveView:
        """
        my live view, created on first use

        Returns:
            the shared LiveView of my camera
        """
        if self.live_view is None:
            grid = Grid(rotation=self.rotation())
            self.live_view = LiveView(
                grid=grid, camera=self.get_camera(), fps=self.fps()
            )
        return self.live_view

    def reset_usb(self) -> dict:
        """
        free the claimed USB device and open the camera anew

        Returns:
            the state of the camera after the reset
        """
        self.get_live_view().stop()
        camera = self.get_camera()
        camera.close()
        OsGPhoto2().free()
        camera.open()
        state = camera.state()
        return state

    def zoom(self, zoom: int, x: float, y: float) -> JSONResponse:
        """
        retune the running live view

        Args:
            zoom: the zoom level - 1 is the full view
            x: the horizontal centre of the magnified area as displayed
            y: the vertical centre of the magnified area as displayed

        Returns:
            JSONResponse: the resulting live view metadata
        """
        live_view = self.get_live_view()
        grid = live_view.grid
        if zoom > 1 and live_view.frame is not None and grid.zoom == 1:
            # the device serves one view at a time so the picture the
            # navigator shows is the last full one
            self.full_frame = live_view.frame
        sensor_x, sensor_y = grid.to_sensor(x, y)
        live_view.tune(zoom, sensor_x, sensor_y)
        meta = live_view.metadata()
        meta["display_x"] = round(x, 4)
        meta["display_y"] = round(y, 4)
        response = JSONResponse(content=meta)
        return response

    def fullview(self) -> Response:
        """
        the last full view frame taken before the magnification

        Returns:
            Response: the JPEG data of the frame or a 503
        """
        frame = self.full_frame
        if frame is None:
            response = Response(content="no full view frame", status_code=503)
        else:
            response = Response(content=frame, media_type="image/jpeg")
        return response

    def liveview_jpg(self) -> Response:
        """
        one frame of the live view

        Returns:
            Response: the JPEG data of the frame or a 503
        """
        live_view = self.get_live_view()
        frame = live_view.snapshot()
        if frame is None:
            response = Response(content="no live view frame", status_code=503)
        else:
            response = Response(content=frame, media_type="image/jpeg")
        return response

    def liveview_mjpg(self) -> StreamingResponse:
        """
        the live view as an MJPEG stream - it carries no zoom parameters so
        that it stays open while the view is retuned

        Returns:
            StreamingResponse: the multipart stream of live view frames
        """
        live_view = self.get_live_view()
        media_type = f"multipart/x-mixed-replace; boundary={BOUNDARY}"
        response = StreamingResponse(live_view.frames(), media_type=media_type)
        return response

    def state(self) -> JSONResponse:
        """
        the camera and server state

        Returns:
            JSONResponse: the state as JSON
        """
        camera = self.get_camera()
        state = camera.state()
        live_view = self.get_live_view()
        grid = live_view.grid
        state["rotation"] = grid.rotation
        state["zoom"] = grid.zoom
        state["zoom_levels"] = self.ZOOM_LEVELS
        state["x"] = grid.x
        state["y"] = grid.y
        state["fps"] = self.fps()
        state["viewers"] = live_view.viewers
        response = JSONResponse(content=state)
        return response


class Cam2WebSolution(InputWebSolution):
    """
    the cam2web solution
    """

    def __init__(self, webserver: Cam2WebServer, client: Client):
        """
        Initialize the solution
        """
        super().__init__(webserver, client)
        self.still_count = 0
        self.live_count = 0
        self.navigator_count = 0
        self.centre_x = 0.5
        self.centre_y = 0.5
        self.dragging = False
        self.step_timer = None

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
        options = {level: f"{level}x" for level in Cam2WebServer.ZOOM_LEVELS}
        self.zoom_radio = ui.radio(options, value=1, on_change=self.magnify).props(
            "inline dense"
        )
        for todo in [self.stop_button, self.check_button]:
            todo.disable()

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

    async def home(self):
        """
        the shooting panel - the button bar, the picture, the navigator
        beside it and the metadata below
        """

        def setup_home():
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

        await self.setup_content_div(setup_home)

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
        show the live view metadata beside the picture and log it

        Args:
            meta: the metadata as delivered by the zoom call
        """
        text = " ".join(f"{key}={value}" for key, value in meta.items())
        self.meta_label.set_text(text)
        logging.getLogger("cam2web").info(text)

    def box(self) -> tuple:
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
        if self.zoom_level() <= 1:
            self.navigator.set_content("")
            return
        box_x, box_y = self.box()
        left = max(0.0, min(self.centre_x - box_x / 2, 1.0 - box_x))
        top = max(0.0, min(self.centre_y - box_y / 2, 1.0 - box_y))
        content = (
            f'<rect x="{left*100:.2f}%" y="{top*100:.2f}%" '
            f'width="{box_x*100:.2f}%" height="{box_y*100:.2f}%" '
            'fill="none" stroke="white" stroke-width="2" />'
        )
        self.navigator.set_content(content)

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
        if event.type == "mousedown" or (
            event.type == "mousemove" and getattr(self, "dragging", False)
        ):
            width = self.navigator_size()[0]
            height = self.navigator_size()[1]
            self.centre_x = max(0.0, min(event.image_x / width, 1.0))
            self.centre_y = max(0.0, min(event.image_y / height, 1.0))
            self.retune()

    def navigator_size(self) -> tuple:
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

    def start_stepping(self, dx: int, dy: int):
        """
        step the magnified area while an arrow is held

        Args:
            dx: the horizontal step in sensor pixels
            dy: the vertical step in sensor pixels
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
        timer = getattr(self, "step_timer", None)
        if timer is not None:
            timer.deactivate()
            self.step_timer = None

    # the step grows while an arrow is held - a single sensor pixel is
    # some 0.8 preview pixels and would not be seen at all
    STEP_GROWTH = 1.25
    STEP_MAX = 64.0

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

    def reset(self):
        """
        free the claimed USB device and open the camera anew - the live
        view of all clients ends with it
        """
        self.image.set_source(BLANK_IMAGE)
        self.stop_button.disable()
        self.live_button.enable()
        self.run_busy(
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
        """
        if not self.live_button.enabled:
            self.stop()
        camera = self.webserver.get_camera()
        self.run_busy(
            camera.capture_still,
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
        name = str(self.client.id)
        self.webserver.save_still(name, data)
        self.image.set_source(f"/stills/{name}.jpg?ts={self.still_count}")
