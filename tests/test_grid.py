"""
Created on 2026-08-23

tests for the camera_grid module

see
https://github.com/WolfgangFahl/scan2wiki/issues/38
https://github.com/WolfgangFahl/scan2wiki/issues/39
https://github.com/WolfgangFahl/scan2wiki/issues/41

@author: wf
"""

from io import BytesIO

from ngwidgets.basetest import Basetest
from PIL import Image

from cam.camera_grid import Grid


class TestGrid(Basetest):
    """
    test the standard grid coordinate handling
    """

    def setUp(self):
        """
        setUp the test environment
        """
        Basetest.setUp(self, debug=True, profile=True)


class TestGridRotation(Basetest):
    """
    test the rotation of a grid
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        image = Image.new("RGB", (40, 20), color=(10, 20, 30))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        self.data = buffer.getvalue()

    def test_rotate(self):
        """
        test that the rotation turns the picture and keeps it at 0
        """
        expected_sizes = {0: (40, 20), 90: (20, 40), 180: (40, 20), 270: (20, 40)}
        for rotation, expected in expected_sizes.items():
            grid = Grid(rotation=rotation)
            turned = grid.rotate(self.data)
            grid.update_from_jpeg(turned)
            if self.debug:
                print(f"{rotation}: {grid}")
            self.assertEqual(expected, (grid.width, grid.height))
            if rotation == 0:
                self.assertEqual(self.data, turned)
