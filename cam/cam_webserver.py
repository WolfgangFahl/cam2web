'''
Created on 24.08.2026

@author: wf
'''
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from nicegui.client import Client
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
 
 
class Cam2WebSolution(InputWebSolution):
    """
    the cam2web solution
    """

    def __init__(self, webserver: Cam2WebServer, client: Client):
        """
        Initialize the solution
        """
        super().__init__(webserver, client)