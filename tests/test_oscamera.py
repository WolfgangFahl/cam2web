"""
Created on 2026-08-23

tests for the camera module

@author: wf
"""

import unittest

from ngwidgets.basetest import Basetest

from cam.cam_webserver import Cam2WebServer
from cam.camera_grid import Grid
from cam.os_camera import OsCamera


def os_camera() -> OsCamera:
    """
    the shared OsCamera using the cam2web solutions base path

    Returns:
        the shared OsCamera
    """
    camera = OsCamera.instance(base_path=Cam2WebServer.get_config().base_path)
    return camera


class TestCamera(Basetest):
    """
    test the camera backends
    """

    @classmethod
    def setUpClass(cls):
        """
        open the camera once for all tests
        """
        super().setUpClass()
        cls.camera = os_camera()
        if cls.camera is not None:
            cls.camera.open()

    @classmethod
    def tearDownClass(cls):
        """
        release the camera
        """
        if cls.camera is not None:
            cls.camera.close()
        super().tearDownClass()

    def setUp(self):
        """
        setUp the test environment
        """
        Basetest.setUp(self, debug=True, profile=True)
        self.camera = TestCamera.camera

    def check_grid(self, name: str, expected: Grid, grid: Grid):
        """
        check the given grid against the expected one

        Args:
            name: the grid's name
            expected: the expected Grid
            grid: the Grid to check
        """
        self.assertIsNotNone(grid, name)
        self.assertEqual(expected, grid, name)
        if self.debug:
            print(f"{name}: {grid}")

    @unittest.skipIf(
        Basetest.inPublicCI() or not os_camera().ready(),
        "no physical camera device available",
    )
    def testCamera(self):
        """
        test a real camera if available
        """
        summary = self.camera.device.get_summary()
        if self.debug:
            print(f"Found \n{summary}")
        grids = {
            "full": self.camera.open(),
            "liveview": self.camera.liveview(),
            "magnify": self.camera.magnify(5),
        }
        expected_grids = {
            "full": self.camera.reference_grid(),
            "liveview": Grid(768, 512, 0),
            "magnify": Grid(768, 512, 0),
        }
        for name, grid in grids.items():
            self.check_grid(name, expected_grids[name], grid)
