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
    """
    width: int = 0
    height: int = 0
    rotation: int = 0  # 0,90,180,270 are allowed
    image: Optional[Image.Image] = field(default=None, compare=False, repr=False)

    @classmethod
    def from_jpeg(cls, data: bytes, rotation: int = 0) -> "Grid":
        """
        create a Grid from the given JPEG bytes
        """
        image = Image.open(BytesIO(bytes(data)))
        grid = cls(width=image.width, height=image.height, rotation=rotation, image=image)
        return grid

    def __str__(self) -> str:
        """
        show me as my constructor call
        """
        text = f"Grid({self.width},{self.height},{self.rotation})"
        return text
