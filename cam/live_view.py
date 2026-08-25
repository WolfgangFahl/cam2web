"""
Created on 2026-08-25

live_view - the shared live view frame source of cam2web
see https://github.com/WolfgangFahl/cam2web/issues/4
    https://github.com/WolfgangFahl/cam2web/issues/6

@author: wf
"""

import asyncio
import threading
import time
from typing import AsyncGenerator, Optional

from cam.camera import Camera
from cam.camera_grid import Grid

BOUNDARY = "frame"


class LiveView:
    """
    the single shared live view of one camera

    a gphoto2 device serves one preview capture at a time so all viewers
    are fed from the latest frame of my own capture loop
    """

    def __init__(self, grid: Grid, camera: Camera, fps: float = 10.0):
        """
        construct me for the given grid and camera

        Args:
            grid: the specification of the view I serve
            camera: the camera to capture preview frames from
            fps: the maximum frames per second to capture with
        """
        self.grid = grid
        self.camera = camera
        self.fps = fps
        self.frame: Optional[bytes] = None
        self.viewers = 0
        self.running = False
        self.error: Optional[Exception] = None
        self.lock = threading.RLock()
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """
        switch the camera to the live view of my grid and start my capture
        loop
        """
        with self.lock:
            if not self.running:
                self.error = None
                try:
                    self.camera.start_liveview(self.grid.zoom)
                    self.running = True
                    self.thread = threading.Thread(
                        target=self.capture_loop, daemon=True
                    )
                    self.thread.start()
                except Exception as ex:
                    self.error = ex

    def stop(self) -> None:
        """
        stop my capture loop and release the camera's live view
        """
        with self.lock:
            was_running = self.running
            self.running = False
            thread = self.thread
            self.thread = None
        if thread is not None:
            thread.join(timeout=self.delay() * 4)
        if was_running:
            try:
                self.camera.stop_liveview()
            except Exception as ex:
                self.error = ex
        self.frame = None

    def delay(self) -> float:
        """
        the seconds between two captured frames

        Returns:
            the frame delay in seconds
        """
        delay = 1.0 / self.fps if self.fps > 0 else 0.1
        return delay

    def capture_loop(self) -> None:
        """
        capture preview frames until I am stopped or the camera fails
        """
        delay = self.delay()
        while self.running:
            try:
                frame = self.camera.preview()
                self.grid.update_from_jpeg(frame)
                self.frame = frame
            except Exception as ex:
                self.error = ex
                self.running = False
            time.sleep(delay)

    def latest(self, timeout: float = 5.0) -> Optional[bytes]:
        """
        the latest captured frame, starting me when needed

        Args:
            timeout: the seconds to wait for the first frame

        Returns:
            the JPEG data of the latest frame or None when none arrived
        """
        self.start()
        deadline = time.time() + timeout
        while self.frame is None and self.running and time.time() < deadline:
            time.sleep(self.delay())
        frame = self.frame
        return frame

    def snapshot(self, timeout: float = 5.0) -> Optional[bytes]:
        """
        a single frame - the camera's live view is released again unless
        a viewer is streaming

        Args:
            timeout: the seconds to wait for the frame

        Returns:
            the JPEG data of the frame or None when none arrived
        """
        frame = self.latest(timeout)
        if self.viewers <= 0:
            self.stop()
        return frame

    async def first_frame(self, timeout: float = 5.0) -> Optional[bytes]:
        """
        the latest captured frame without blocking the event loop

        Args:
            timeout: the seconds to wait for the first frame

        Returns:
            the JPEG data of the latest frame or None when none arrived
        """
        await asyncio.to_thread(self.start)
        deadline = time.time() + timeout
        while self.frame is None and self.running and time.time() < deadline:
            await asyncio.sleep(self.delay())
        frame = self.frame
        return frame

    def part(self, frame: bytes) -> bytes:
        """
        the multipart chunk for the given frame

        Args:
            frame: the JPEG data of the frame

        Returns:
            the chunk as sent to an MJPEG client
        """
        header = (
            f"--{BOUNDARY}\r\n"
            f"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(frame)}\r\n\r\n"
        )
        chunk = header.encode() + frame + b"\r\n"
        return chunk

    async def frames(self) -> AsyncGenerator[bytes, None]:
        """
        the MJPEG chunks for one viewer - I stop when the last viewer left

        the generator is asynchronous so that a disconnecting client
        cancels it and my viewer accounting stays correct

        Yields:
            the multipart chunks of the stream
        """
        with self.lock:
            self.viewers += 1
        try:
            frame = await self.first_frame()
            while frame is not None and self.running:
                yield self.part(frame)
                await asyncio.sleep(self.delay())
                frame = self.frame
        finally:
            with self.lock:
                self.viewers -= 1
                is_last = self.viewers <= 0
            if is_last:
                await asyncio.to_thread(self.stop)
