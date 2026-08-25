"""
Created on 2026-08-25

test the shared live view frame source

@author: wf
"""

import asyncio
import unittest

from ngwidgets.basetest import Basetest

from cam.camera_grid import Grid
from cam.live_view import LiveView
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
