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

    def test_to_sensor(self):
        """
        test that a point the user aims at is turned back to the sensor
        """
        expected = {
            0: (0.25, 0.75),
            90: (0.75, 0.75),
            180: (0.75, 0.25),
            270: (0.25, 0.25),
        }
        for rotation, sensor in expected.items():
            grid = Grid(rotation=rotation)
            result = grid.to_sensor(0.25, 0.75)
            if self.debug:
                print(f"{rotation}: 0.25,0.75 -> {result}")
            self.assertEqual(sensor, result)

    def test_to_display_is_the_inverse(self):
        """
        test that display and sensor fractions turn into each other
        """
        for rotation in [0, 90, 180, 270]:
            grid = Grid(rotation=rotation)
            sensor = grid.to_sensor(0.25, 0.75)
            display = grid.to_display(*sensor)
            if self.debug:
                print(f"{rotation}: {sensor} -> {display}")
            self.assertAlmostEqual(0.25, display[0])
            self.assertAlmostEqual(0.75, display[1])

    def test_to_display_box(self):
        """
        test that a box swaps its sides on a quarter turn
        """
        expected = {0: (0.2, 0.4), 90: (0.4, 0.2), 180: (0.2, 0.4), 270: (0.4, 0.2)}
        for rotation, box in expected.items():
            grid = Grid(rotation=rotation)
            result = grid.to_display_box(0.2, 0.4)
            if self.debug:
                print(f"{rotation}: {result}")
            self.assertEqual(box, result)

    def test_crop(self):
        """
        test that the digital magnification crops around the centre
        """
        grid = Grid()
        for factor, expected in [(1, (40, 20)), (2, (20, 10)), (4, (10, 5))]:
            cropped = grid.crop(self.data, factor)
            image = Image.open(BytesIO(cropped))
            if self.debug:
                print(f"{factor}: {image.width}x{image.height}")
            self.assertEqual(expected, (image.width, image.height))
