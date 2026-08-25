"""
Created on 2026-08-25

test the cam2web webserver REST interface

@author: wf
"""

import json
import time
import unittest
from io import BytesIO

from ngwidgets.basetest import Basetest
from ngwidgets.webserver_test import WebserverTest
from nicegui import core
from PIL import Image

from cam.cam2web_cmd import Cam2WebCmd
from cam.cam_webserver import Cam2WebServer
from cam.camera_grid import Grid
from cam.live_view import LiveView
from tests.test_oscamera import os_camera


class TestCam2WebServer(WebserverTest):
    """
    test the cam2web webserver
    """

    def setUp(self, debug=True, profile=True):
        server_class = Cam2WebServer
        cmd_class = Cam2WebCmd
        WebserverTest.setUp(
            self,
            server_class=server_class,
            cmd_class=cmd_class,
            debug=debug,
            profile=profile,
        )
        pass

    def tearDown(self):
        """
        release the camera so device tests can claim it again
        """
        camera = self.ws.camera
        if camera:
            camera.close()
        WebserverTest.tearDown(self)

    def test_home(self):
        """
        test the shooting panel page
        """
        # we wait 1 sec more than the official timeout
        deadline = time.time() + self.ws.config.timeout + 1.0
        # the nicegui page needs the event loop of the server thread
        while core.loop is None and time.time() < deadline:
            time.sleep(0.1)
        html = self.get_html("/")
        self.assertTrue("<title>cam2web" in html)

    def test_state_json(self):
        """
        test the /api/state.json endpoint
        """
        state = self.get_json("/api/state.json")
        if self.debug:
            print(json.dumps(state, indent=2))
        expected_keys = [
            "present",
            "open",
            "platform",
            "size",
            "rotation",
            "fps",
            "viewers",
        ]
        for key in expected_keys:
            self.assertIn(key, state)
        self.assertIn("width", state["size"])
        self.assertIn("height", state["size"])

    @unittest.skipIf(
        Basetest.inPublicCI() or not os_camera().ready(),
        "no physical camera device available",
    )
    def test_still_jpg(self):
        """
        test the /api/still.jpg endpoint against the reference picture
        """
        response = self.get_response("/api/still.jpg")
        data = response.content
        grid = Grid.from_jpeg(data)
        expected = os_camera().reference_grid()
        if self.debug:
            print(f"still: {grid} reference: {expected}")
        self.assertEqual(expected.width, grid.width)
        self.assertEqual(expected.height, grid.height)

    def test_liveview_routes(self):
        """
        test that the live view routes are registered - no device needed
        """
        paths = [route.path for route in self.ws.app.routes]
        if self.debug:
            print(paths)
        self.assertIn("/api/liveview.jpg", paths)
        self.assertIn("/api/liveview.mjpg", paths)

    @unittest.skipIf(
        Basetest.inPublicCI() or not os_camera().ready(),
        "no physical camera device available",
    )
    def test_reset_usb(self):
        """
        test freeing the claimed device and opening the camera anew
        """
        state = self.ws.reset_usb()
        if self.debug:
            print(state)
        self.assertTrue(state["present"])
        self.assertTrue(state["open"])

    @unittest.skipIf(
        Basetest.inPublicCI() or not os_camera().ready(),
        "no physical camera device available",
    )
    def test_liveview_jpg(self):
        """
        test the /api/liveview.jpg endpoint
        """
        response = self.get_response("/api/liveview.jpg")
        data = response.content
        grid = Grid.from_jpeg(data)
        if self.debug:
            print(f"live view: {grid}")
        self.assertEqual("image/jpeg", response.headers["content-type"])
        self.assertTrue(grid.width > 0)
        self.ws.get_live_view().stop()

    @unittest.skipIf(
        Basetest.inPublicCI() or not os_camera().ready(),
        "no physical camera device available",
    )
    def test_summary_txt(self):
        """
        test the /api/summary.txt endpoint
        """
        response = self.get_response("/api/summary.txt")
        summary = response.text
        if self.debug:
            print(summary)
        self.assertTrue(len(summary) > 0)


class TestStillDuringLiveView(Basetest):
    """
    test that a still capture owns the device alone - no device needed
    """

    class FakeCamera:
        """
        a camera that refuses a capture while its live view runs, as the
        device does with "[-110] I/O Operation in Arbeit"
        """

        def __init__(self):
            self.grid = Grid(width=3888, height=2592)
            self.live = False
            self.captures = 0
            image = Image.new("RGB", (768, 512), color=(10, 20, 30))
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            self.frame = buffer.getvalue()

        def start_liveview(self, level: int = 1, position: str = None) -> None:
            self.live = True

        def stop_liveview(self) -> None:
            self.live = False

        def preview(self) -> bytes:
            return self.frame

        def capture_still(self) -> bytes:
            if self.live:
                raise Exception("[-110] I/O Operation in Arbeit")
            self.captures += 1
            return b"still"

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.camera = self.FakeCamera()
        self.server = Cam2WebServer()
        self.server.camera = self.camera
        self.server.live_view = LiveView(grid=Grid(), camera=self.camera, fps=20.0)

    def tearDown(self):
        self.server.live_view.stop()
        Basetest.tearDown(self)

    def test_capture_still_switches_the_live_view_off_and_on(self):
        """
        test that a still taken while the live view runs succeeds and
        leaves the live view running for the viewers
        """
        live_view = self.server.live_view
        live_view.viewers = 1
        live_view.start()
        self.assertTrue(live_view.running)
        data = self.server.capture_still()
        if self.debug:
            print(f"captures {self.camera.captures} running {live_view.running}")
        self.assertEqual(b"still", data)
        self.assertEqual(1, self.camera.captures)
        self.assertTrue(live_view.running)

    def test_capture_still_leaves_the_live_view_off_without_viewers(self):
        """
        test that a still taken without viewers does not restart the
        live view
        """
        live_view = self.server.live_view
        live_view.viewers = 0
        live_view.start()
        data = self.server.capture_still()
        if self.debug:
            print(f"running after capture {live_view.running}")
        self.assertEqual(b"still", data)
        self.assertFalse(live_view.running)
