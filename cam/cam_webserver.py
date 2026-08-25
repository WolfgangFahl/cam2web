'''
Created on 24.08.2026

@author: wf
'''
from typing import Optional

import os

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

from cam.live_view import BOUNDARY, LiveView
from cam.os_camera import OsCamera
from cam.version import Version

BLANK_IMAGE = (
    "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
)


class Cam2WebServer(InputWebserver):
    """
    web interface for gphoto2 cams

    webcam emulator server - serves an MJPEG stream and stills
    """

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
            "view is started when it is not running yet",
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
            "last viewer left",
        )
        def liveview_mjpg() -> StreamingResponse:
            """
            the continuous live view
            """
            return self.liveview_mjpg()

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
        fps = getattr(getattr(self, "args", None), "fps", 10.0)
        return fps

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
        data = camera.capture_still()
        response = Response(content=data, media_type="image/jpeg")
        return response

    def get_live_view(self) -> LiveView:
        """
        my live view, created on first use

        Returns:
            the shared LiveView of my camera
        """
        if self.live_view is None:
            self.live_view = LiveView(camera=self.get_camera(), fps=self.fps())
        return self.live_view

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
        the live view as an MJPEG stream

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
        state["fps"] = self.fps()
        state["viewers"] = self.get_live_view().viewers
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

    def setup_buttons(self):
        """
        the button bar of https://github.com/WolfgangFahl/cam2web/issues/8 -
        shoot, live view and stop are active yet, the others are placeholders
        """
        self.shoot_button = ui.button("Shoot", icon="camera", on_click=self.shoot)
        self.live_button = ui.button("Live view", icon="videocam", on_click=self.live)
        self.stop_button = ui.button("Stop", icon="stop", on_click=self.stop)
        self.check_button = ui.button("Check camera", icon="help")
        self.reset_button = ui.button("Reset USB", icon="usb")
        self.rotate_left_button = ui.button(icon="rotate_left")
        self.rotate_right_button = ui.button(icon="rotate_right")
        self.magnify_switch = ui.switch("Magnify")
        for todo in [
            self.stop_button,
            self.check_button,
            self.reset_button,
            self.rotate_left_button,
            self.rotate_right_button,
            self.magnify_switch,
        ]:
            todo.disable()

    async def home(self):
        """
        the shooting panel - the button bar with the picture below
        """

        def setup_home():
            with ui.column().classes("w-full gap-3") as self.container:
                with ui.row().classes("items-center gap-2"):
                    self.setup_buttons()
                    self.spinner = ui.spinner()
                    self.spinner.set_visibility(False)
                    self.status = ui.label("idle")
                self.image = ui.image("").style("max-width:70%;min-height:512px")

        await self.setup_content_div(setup_home)

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
