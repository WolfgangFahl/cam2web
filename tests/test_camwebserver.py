"""
Created on 2026-08-25

test the cam2web webserver REST interface

@author: wf
"""

import json
import time
import unittest

from ngwidgets.basetest import Basetest
from ngwidgets.webserver_test import WebserverTest
from nicegui import core

from cam.cam2web_cmd import Cam2WebCmd
from cam.cam_webserver import Cam2WebServer
from cam.camera_grid import Grid
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
        # the nicegui page needs the event loop of the server thread
        deadline = time.time() + 5.0
        while core.loop is None and time.time() < deadline:
            time.sleep(0.1)
        html = self.get_html("/")
        self.assertTrue(len(html) > 0)

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
