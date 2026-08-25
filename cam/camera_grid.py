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
from typing import Optional, Tuple

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

    def to_sensor(self, display_x: float, display_y: float) -> Tuple[float, float]:
        """
        the sensor fractions for the given display fractions

        the served picture is turned clockwise by my rotation, so a point
        the user points at has to be turned back to address the sensor

        Args:
            display_x: the horizontal fraction as seen by the user
            display_y: the vertical fraction as seen by the user

        Returns:
            the x and y fraction on the sensor
        """
        if self.rotation == 90:
            sensor = (display_y, 1.0 - display_x)
        elif self.rotation == 180:
            sensor = (1.0 - display_x, 1.0 - display_y)
        elif self.rotation == 270:
            sensor = (1.0 - display_y, display_x)
        else:
            sensor = (display_x, display_y)
        return sensor

    def to_display(self, sensor_x: float, sensor_y: float) -> Tuple[float, float]:
        """
        the display fractions for the given sensor fractions

        Args:
            sensor_x: the horizontal fraction on the sensor
            sensor_y: the vertical fraction on the sensor

        Returns:
            the x and y fraction as seen by the user
        """
        if self.rotation == 90:
            display = (1.0 - sensor_y, sensor_x)
        elif self.rotation == 180:
            display = (1.0 - sensor_x, 1.0 - sensor_y)
        elif self.rotation == 270:
            display = (sensor_y, 1.0 - sensor_x)
        else:
            display = (sensor_x, sensor_y)
        return display

    def to_display_box(self, box_x: float, box_y: float) -> Tuple[float, float]:
        """
        the display size of a sensor sized box - width and height swap
        on a quarter turn

        Args:
            box_x: the box width as a fraction of the sensor width
            box_y: the box height as a fraction of the sensor height

        Returns:
            the box width and height as display fractions
        """
        box = (box_y, box_x) if self.rotation in (90, 270) else (box_x, box_y)
        return box

    def crop(self, data: bytes, factor: int) -> bytes:
        """
        the centred crop of the given JPEG magnifying it by the given factor

        Args:
            data: the JPEG data to crop
            factor: the digital magnification - 1 leaves the data alone

        Returns:
            the cropped JPEG data
        """
        cropped = bytes(data)
        if factor > 1:
            image = Image.open(BytesIO(cropped))
            width = image.width // factor
            height = image.height // factor
            left = (image.width - width) // 2
            top = (image.height - height) // 2
            image = image.crop((left, top, left + width, top + height))
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            cropped = buffer.getvalue()
        return cropped

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
