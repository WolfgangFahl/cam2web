'''
Created on 24.08.2026

@author: wf
'''
from typing import Optional

from fastapi.responses import JSONResponse, PlainTextResponse, Response
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from nicegui import app
from nicegui.client import Client

from cam.os_camera import OsCamera
from cam.version import Version


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
        self.viewers = 0

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

    def state(self) -> JSONResponse:
        """
        the camera and server state

        Returns:
            JSONResponse: the state as JSON
        """
        camera = self.get_camera()
        state = camera.state()
        state["fps"] = self.fps()
        state["viewers"] = self.viewers
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
