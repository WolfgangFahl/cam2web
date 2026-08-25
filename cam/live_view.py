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

    # frames the device is given to follow a zoom or position change -
    # measured on an EOS 1000D where a change needs some 0.6 s
    SETTLE_FRAMES = 6

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
        self.frame_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.applied_zoom: Optional[int] = None
        self.applied_position: Optional[str] = None
        self.settling = 0

    def start(self) -> None:
        """
        switch the camera to the live view of my grid and start my capture
        loop
        """
        with self.lock:
            if not self.running:
                self.error = None
                try:
                    # the device refuses a zoom at live view start, so the
                    # full view is started and the zoom follows in the loop
                    self.camera.start_liveview()
                    self.applied_zoom = 1
                    self.applied_position = None
                    self.running = True
                    self.thread = threading.Thread(
                        target=self.capture_loop, daemon=True
                    )
                    self.thread.start()
                except Exception as ex:
                    self.error = ex

    def position(self) -> Optional[str]:
        """
        the device position of my grid's magnified area

        Returns:
            the eoszoomposition or None when the camera can not tell
        """
        position = None
        if hasattr(self.camera, "zoom_position"):
            position = self.camera.zoom_position(self.grid)
        return position

    def apply_step(self) -> bool:
        """
        hand one pending change to the device

        zoom and position each need their own frames to be taken before the
        next change is accepted, so at most one step is done per round and
        only by my capture loop - gphoto2 serves one caller

        Returns:
            True while the device is following a change and its frames are
            not the ones the grid asks for
        """
        position = self.position()
        if self.settling > 0:
            self.settling -= 1
        elif self.grid.zoom != self.applied_zoom:
            self.camera.set_zoom_level(self.grid.zoom)
            self.applied_zoom = self.grid.zoom
            self.settling = self.SETTLE_FRAMES
        elif position is not None and position != self.applied_position:
            self.camera.set_zoom_position(position)
            self.applied_position = position
            self.settling = self.SETTLE_FRAMES
        is_settling = self.settling > 0
        return is_settling

    def tune(self, zoom: int, x: float, y: float) -> None:
        """
        serve the magnified area given by zoom, x and y

        Args:
            zoom: the zoom level - 1 is the full view
            x: the horizontal centre of the magnified area
            y: the vertical centre of the magnified area
        """
        with self.lock:
            changed = (zoom, x, y) != (self.grid.zoom, self.grid.x, self.grid.y)
            self.grid.zoom = zoom
            self.grid.x = x
            self.grid.y = y
            if changed:
                # the capture loop owns the device and applies the change,
                # the frames until then are the ones of the old area
                self.frame = None
                self.frame_event.clear()

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
        # wake the waiters so they see that I am not running any more
        self.frame_event.set()

    def delay(self) -> float:
        """
        the seconds between two captured frames

        Returns:
            the frame delay in seconds 1.0 / self.fps if fps is set otherwise 0.1
        """
        delay = 1.0 / self.fps if self.fps > 0 else 0.1
        return delay

    def capture_loop(self) -> None:
        """
        capture preview frames until I am stopped or the camera fails

        the sleep is the frame rate limit itself - every other wait in me
        is done on the frame event
        """
        delay = self.delay()
        while self.running:
            try:
                frame = self.camera.preview()
                if not self.apply_step():
                    frame = self.grid.rotate(frame)
                    self.grid.update_from_jpeg(frame)
                    self.frame = frame
                    self.frame_event.set()
            except Exception as ex:
                self.error = ex
                self.running = False
                self.frame_event.set()
            time.sleep(delay)

    def next_frame(self, timeout: float) -> Optional[bytes]:
        """
        the next frame published by my capture loop

        Args:
            timeout: the seconds to wait for it

        Returns:
            the JPEG data of the frame or None when none arrived in time
        """
        self.frame_event.wait(timeout)
        self.frame_event.clear()
        frame = self.frame
        return frame

    def latest(self, timeout: float = 5.0) -> Optional[bytes]:
        """
        the latest captured frame, starting me when needed

        Args:
            timeout: the seconds to wait for the first frame

        Returns:
            the JPEG data of the latest frame or None when none arrived
        """
        self.start()
        frame = self.frame if self.frame else self.next_frame(timeout)
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
        frame = await asyncio.to_thread(self.latest, timeout)
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

    async def frames(self, timeout: float = 5.0) -> AsyncGenerator[bytes, None]:
        """
        the MJPEG chunks for one viewer - one chunk per captured frame so
        that no picture is sent twice; I stop when the last viewer left

        the generator is asynchronous so that a disconnecting client
        cancels it and my viewer accounting stays correct

        Args:
            timeout: the seconds to wait for each frame

        Yields:
            the multipart chunks of the stream
        """
        with self.lock:
            self.viewers += 1
        try:
            frame = await self.first_frame(timeout)
            while frame is not None and self.running:
                yield self.part(frame)
                frame = await asyncio.to_thread(self.next_frame, timeout)
        finally:
            with self.lock:
                self.viewers -= 1
                is_last = self.viewers <= 0
            if is_last:
                await asyncio.to_thread(self.stop)
