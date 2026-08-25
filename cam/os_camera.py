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

        Returns:
            the Grid of my reference picture
        """
        grid = None
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

    def capture_reference(self, path: str) -> None:
        """
        capture my reference picture to the given path

        Args:
            path: the path to save my reference picture to
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        camera_path = self.device.capture(gp.GP_CAPTURE_IMAGE)
        camera_file = self.device.file_get(
            camera_path.folder, camera_path.name, gp.GP_FILE_TYPE_NORMAL
        )
        camera_file.save(path)

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
