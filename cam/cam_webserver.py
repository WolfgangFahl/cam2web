"""
Created on 2026-08-24

@author: wf
"""

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

from cam.cam_view import CamView
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

    def capture_still(self) -> bytes:
        """
        capture a still at full resolution

        the device serves either the live view or the shutter, never both -
        gphoto2 answers a capture during a running live view with
        "I/O Operation in Arbeit", so the live view is switched off for the
        capture and started again when viewers are still connected

        Returns:
            the JPEG data of the still, turned by the current rotation
        """
        camera = self.get_camera()
        live_view = self.get_live_view()
        was_running = live_view.running
        if was_running:
            live_view.stop()
        try:
            data = live_view.grid.rotate(camera.capture_still())
        finally:
            if was_running and live_view.viewers > 0:
                live_view.start()
        return data

    def still(self) -> Response:
        """
        a still captured at full resolution

        Returns:
            Response: the JPEG data of the still
        """
        data = self.capture_still()
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
    the cam2web solution - one CamView per client
    """

    def __init__(self, webserver: "Cam2WebServer", client: Client):
        """
        Initialize the solution
        """
        super().__init__(webserver, client)
        self.cam_view = CamView(self)

    async def home(self):
        """
        the shooting panel
        """

        def setup_home():
            self.cam_view.setup_ui()

        await self.setup_content_div(setup_home)
