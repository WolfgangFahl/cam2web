"""
Created on 2026-08-23

camera_grid - cam2web pixel grid

https://github.com/WolfgangFahl/scan2wiki/issues/38
https://github.com/WolfgangFahl/scan2wiki/issues/39
https://github.com/WolfgangFahl/scan2wiki/issues/41

@author: wf
"""

from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional

from PIL import Image


@dataclass
class Grid:
    """
    The pixel grid as seen by a user

    the grid is the specification of a view - which part of the sensor at
    which zoom level and rotation - and carries the picture last seen in it
    """

    width: int = 0
    height: int = 0
    rotation: int = 0  # 0,90,180,270 are allowed
    zoom: int = 1  # 1 is the full view, higher values magnify
    x: float = 0.5  # centre of the magnified area, 0..1 of the sensor
    y: float = 0.5  # independent of the rotation
    image: Optional[Image.Image] = field(default=None, compare=False, repr=False)

    @classmethod
    def from_jpeg(
        cls,
        data: bytes,
        rotation: int = 0,
        zoom: int = 1,
        x: float = 0.5,
        y: float = 0.5,
    ) -> "Grid":
        """
        create a Grid from the given JPEG bytes

        Args:
            data: the JPEG data of the picture
            rotation: the clockwise rotation in degrees
            zoom: the zoom level the picture was taken at
            x: the horizontal centre of the magnified area
            y: the vertical centre of the magnified area

        Returns:
            the Grid of the picture
        """
        image = Image.open(BytesIO(bytes(data)))
        grid = cls(
            width=image.width,
            height=image.height,
            rotation=rotation,
            zoom=zoom,
            x=x,
            y=y,
            image=image,
        )
        return grid

    def rotate(self, data: bytes) -> bytes:
        """
        turn the given JPEG by my rotation

        Args:
            data: the JPEG data to turn

        Returns:
            the turned JPEG data - the data itself when I am not rotated
        """
        turned = bytes(data)
        if self.rotation:
            image = Image.open(BytesIO(turned))
            image = image.rotate(-self.rotation, expand=True)
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            turned = buffer.getvalue()
        return turned

    def update_from_jpeg(self, data: bytes) -> None:
        """
        take size and picture from the given JPEG, keeping my specification

        Args:
            data: the JPEG data of the picture
        """
        image = Image.open(BytesIO(bytes(data)))
        self.width = image.width
        self.height = image.height
        self.image = image

    def __str__(self) -> str:
        """
        show me as my constructor call
        """
        text = f"Grid({self.width},{self.height},{self.rotation},{self.zoom},{self.x},{self.y})"
        return text
