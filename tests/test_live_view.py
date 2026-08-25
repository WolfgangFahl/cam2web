"""
Created on 2026-08-25

test the shared live view frame source

@author: wf
"""

import asyncio
import unittest

from ngwidgets.basetest import Basetest

from cam.camera import Camera
from cam.camera_grid import Grid
from cam.live_view import LiveView
from cam.os_camera import OsCamera
from tests.test_oscamera import os_camera


class TestLiveView(Basetest):
    """
    test the LiveView frame source
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.camera = os_camera()
        self.grid = Grid()
        self.live_view = LiveView(grid=self.grid, camera=self.camera, fps=5.0)

    def tearDown(self):
        self.live_view.stop()
        Basetest.tearDown(self)

    def test_part(self):
        """
        test the multipart chunk of a frame - no device needed
        """
        frame = b"jpegdata"
        chunk = self.live_view.part(frame)
        if self.debug:
            print(chunk)
        self.assertTrue(chunk.startswith(b"--frame\r\n"))
        self.assertIn(b"Content-Type: image/jpeg", chunk)
        self.assertIn(b"Content-Length: 8", chunk)
        self.assertTrue(chunk.endswith(frame + b"\r\n"))

    def test_delay(self):
        """
        test the frame delay - no device needed
        """
        self.assertAlmostEqual(0.2, self.live_view.delay())
        self.live_view.fps = 0
        self.assertAlmostEqual(0.1, self.live_view.delay())

    @unittest.skipIf(
        Basetest.inPublicCI() or not os_camera().ready(),
        "no physical camera device available",
    )
    def test_latest(self):
        """
        test capturing live view frames from the device
        """
        frame = self.live_view.latest()
        self.assertIsNotNone(frame)
        grid = Grid.from_jpeg(frame)
        if self.debug:
            print(f"live view frame: {grid} {len(frame)} bytes")
        self.assertTrue(grid.width > 0)
        self.assertTrue(grid.height > 0)
        self.assertEqual(grid.width, self.grid.width)
        self.assertEqual(grid.height, self.grid.height)
        self.assertEqual(1, self.grid.zoom)
        self.assertTrue(self.live_view.running)
        self.live_view.stop()
        self.assertFalse(self.live_view.running)

    @unittest.skipIf(
        Basetest.inPublicCI() or not os_camera().ready(),
        "no physical camera device available",
    )
    def test_frames(self):
        """
        test the multipart stream and the viewer accounting
        """

        async def one_chunk() -> bytes:
            """
            take a single chunk from the stream and leave it like a
            disconnecting client does

            Returns:
                the first multipart chunk
            """
            frames = self.live_view.frames()
            chunk = await frames.__anext__()
            self.assertEqual(1, self.live_view.viewers)
            await frames.aclose()
            return chunk

        chunk = asyncio.run(one_chunk())
        self.assertTrue(chunk.startswith(b"--frame\r\n"))
        self.assertEqual(0, self.live_view.viewers)
        self.assertFalse(self.live_view.running)


class TestLiveViewTuning(Basetest):
    """
    test the zoom tuning of a live view without a device
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.grid = Grid()
        self.live_view = LiveView(grid=self.grid, camera=Camera(), fps=5.0)

    def test_tune(self):
        """
        test that tuning writes zoom, x and y into the grid
        """
        self.live_view.tune(5, 0.25, 0.75)
        if self.debug:
            print(self.grid)
        self.assertEqual(5, self.grid.zoom)
        self.assertEqual(0.25, self.grid.x)
        self.assertEqual(0.75, self.grid.y)

    def test_zoom_position(self):
        """
        test the sensor pixel position of a magnified area
        """
        camera = OsCamera()
        camera.grid = Grid(width=4000, height=2000)
        cases = {
            (1, 0.5, 0.5): None,  # the full view has no position
            (5, 0.5, 0.5): "1600,800",
            (5, 0.0, 0.0): "0,0",
            (5, 1.0, 1.0): "3200,1600",
        }
        for (zoom, x, y), expected in cases.items():
            grid = Grid(zoom=zoom, x=x, y=y)
            position = camera.zoom_position(grid)
            if self.debug:
                print(f"{grid}: {position}")
            self.assertEqual(expected, position)


class FakeCamera:
    """
    a camera that only records what was asked of it
    """

    def __init__(self, width: int = 3888, height: int = 2592):
        self.grid = Grid(width=width, height=height)
        self.zoom_levels = []
        self.positions = []

    def zoom_position(self, grid: Grid, level: int = None) -> str:
        """
        the position as OsCamera computes it
        """
        position = OsCamera.zoom_position(self, grid, level)
        return position

    def set_zoom_level(self, level: int) -> None:
        self.zoom_levels.append(level)

    def set_zoom_position(self, position: str) -> None:
        self.positions.append(position)


class TestZoomSteps(Basetest):
    """
    test the zoom and position steps handed to the device - no device needed
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.camera = FakeCamera()
        self.grid = Grid()
        self.live_view = LiveView(grid=self.grid, camera=self.camera, fps=20.0)

    def settle(self, rounds: int = 12) -> None:
        """
        let the apply steps run without a capture loop
        """
        for _ in range(rounds):
            self.live_view.apply_step()

    def test_device_and_digital_zoom(self):
        """
        test that zoom 10 is the device's 5 magnified twice more
        """
        expected = {1: (1, 1), 5: (5, 1), 10: (5, 2)}
        for zoom, (device, digital) in expected.items():
            self.grid.zoom = zoom
            result = (self.live_view.device_zoom(), self.live_view.digital_zoom())
            if self.debug:
                print(f"zoom {zoom}: device,digital {result}")
            self.assertEqual((device, digital), result)

    def test_position_is_reapplied_after_a_zoom_change(self):
        """
        test that going back to the full view and magnifying again sends
        the position anew - the device recentres on a zoom change
        """
        self.live_view.applied_zoom = 1
        self.live_view.tune(5, 0.25, 0.25)
        self.settle()
        first = list(self.camera.positions)
        self.live_view.tune(1, 0.25, 0.25)
        self.settle()
        self.live_view.tune(5, 0.25, 0.25)
        self.settle()
        if self.debug:
            print(f"levels {self.camera.zoom_levels} positions {self.camera.positions}")
        self.assertTrue(len(first) >= 1)
        self.assertTrue(len(self.camera.positions) > len(first))
        self.assertEqual(first[-1], self.camera.positions[-1])

    def test_metadata(self):
        """
        test that the metadata shows what is going on
        """
        self.live_view.applied_zoom = 1
        self.live_view.tune(10, 0.75, 0.25)
        self.settle()
        meta = self.live_view.metadata()
        if self.debug:
            print(meta)
        self.assertEqual(10, meta["zoom"])
        self.assertEqual(5, meta["device_zoom"])
        self.assertEqual(2, meta["digital_zoom"])
        self.assertEqual(0.75, meta["sensor_x"])
        self.assertIsNotNone(meta["position"])
