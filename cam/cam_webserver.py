'''
Created on 24.08.2026

@author: wf
'''
from typing import Optional

from fastapi.responses import JSONResponse, PlainTextResponse
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

        @app.get("/api/state.json")
        def state():
            return self.state()

        @app.get("/api/summary.txt")
        def summary():
            return self.summary()

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
        base_path = getattr(getattr(self, "args", None), "base_path", None)
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
