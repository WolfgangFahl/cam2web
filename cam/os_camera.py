"""
Created on 2026-08-04

@author: wf
"""

import os
import sys
from dataclasses import dataclass, field
from io import BytesIO
from typing import ClassVar, Optional

from PIL import Image

from cam.camera import Camera
from cam.camera_grid import Grid
from cam.os_gphoto2 import OsGPhoto2

try:
    import gphoto2 as gp
except ImportError:
    gp = None  # type: ignore


@dataclass
class OsCamera(Camera):
    """
    Operating system aware camera
    """

    base_path: Optional[str] = None
    grid: Optional[Grid] = field(default=None, compare=False, repr=False)

    ROTATION_BY_ORIENTATION: ClassVar[dict] = {1: 0, 3: 180, 6: 90, 8: 270}

    def open(self) -> Grid:
        """
        open the camera device and show my reference picture's grid

        a claiming daemon such as ptpcamerad takes the device back as soon
        as it is closed, so a failed claim is retried once after freeing it

        Returns:
            the Grid of my reference picture
        """
        grid = None
        Camera.open(self)
        if not self.opened:
            OsGPhoto2().free()
            self.error = None
            Camera.open(self)
        if self.ready():
            grid = self.reference_grid()
        self.grid = grid
        return grid

    def state(self) -> dict:
        """
        my operating system level state - the device part is delegated
        to Camera

        Returns:
            the camera state as a dict
        """
        state = Camera.state(self)
        width = self.grid.width if self.grid else 0
        height = self.grid.height if self.grid else 0
        rotation = self.grid.rotation if self.grid else 0
        state["platform"] = sys.platform
        state["size"] = {"width": width, "height": height}
        state["rotation"] = rotation
        return state

    def zoom_position(self, grid: Grid, level: Optional[int] = None) -> Optional[str]:
        """
        the eoszoomposition for the magnified area of the given grid

        the grid's x and y are the centre of the area in 0..1 of the sensor
        while the device wants the top left corner in sensor pixels

        Args:
            grid: the grid specifying zoom, x and y
            level: the device zoom level the box is sized for - the grid's
                zoom when not given

        Returns:
            the position as "x,y" or None when my sensor size is unknown
        """
        position = None
        zoom = level if level is not None else grid.zoom
        if self.grid and zoom > 1:
            box_width = self.grid.width // zoom
            box_height = self.grid.height // zoom
            left = int(grid.x * self.grid.width) - box_width // 2
            top = int(grid.y * self.grid.height) - box_height // 2
            left = max(0, min(left, self.grid.width - box_width))
            top = max(0, min(top, self.grid.height - box_height))
            position = f"{left},{top}"
        return position

    def reference_path(self) -> str:
        """
        the path of my reference picture, keyed by my serial number

        Returns:
            the path of my reference picture

        Raises:
            ValueError: if no base_path has been given
        """
        if self.base_path is None:
            raise ValueError("base_path is needed for the reference picture")
        serial = self.config.get_child_by_name("serialnumber").get_value()
        path = os.path.join(self.base_path, f"{serial}.jpg")
        return path

    def capture_still(self) -> bytes:
        """
        capture a still on the camera and fetch its JPEG data

        Returns:
            the JPEG data of the captured still
        """
        Camera.open(self)
        camera_path = self.device.capture(gp.GP_CAPTURE_IMAGE)
        camera_file = self.device.file_get(
            camera_path.folder, camera_path.name, gp.GP_FILE_TYPE_NORMAL
        )
        data = bytes(camera_file.get_data_and_size())
        return data

    def capture_reference(self, path: str) -> None:
        """
        capture my reference picture to the given path

        Args:
            path: the path to save my reference picture to
        """
        data = self.capture_still()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as jpeg_file:
            jpeg_file.write(data)

    def reference_grid(self) -> Grid:
        """
        the Grid of my reference picture, captured once when absent

        Returns:
            the Grid of my reference picture
        """
        path = self.reference_path()
        if not os.path.isfile(path):
            self.capture_reference(path)
        with open(path, "rb") as jpeg_file:
            data = jpeg_file.read()
        image = Image.open(BytesIO(data))
        orientation = image.getexif().get(274, 1)
        rotation = self.ROTATION_BY_ORIENTATION.get(orientation, 0)
        grid = Grid.from_jpeg(data, rotation=rotation)
        return grid
