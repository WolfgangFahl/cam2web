"""
Created on 2026-08-20

camera - camera handling of cam2web
see https://github.com/WolfgangFahl/scan2wiki/issues/33
"""
from typing import Any, ClassVar, Optional

from basemkit.yamlable import lod_storable

from cam.camera_grid import Grid


@lod_storable
class Camera:
    """
    a gphoto2 backed Camera
    """
    error: Optional[Exception] = None
    device: Optional[Any] = None
    opened: bool = False

    _instance: ClassVar[Optional["Camera"]] = None
    
    def ready(self) -> bool:
        """
        True when the camera device is initialized and error free
        """
        is_ready = self.error is None and self.device is not None
        return is_ready


    @classmethod
    def instance(cls, **kwargs) -> "Camera":
        """
        the shared Camera, created once from the attached device

        Args:
            kwargs: the keyword arguments to construct me with
        """
        if cls._instance is None:
            cls._instance = cls.from_device(**kwargs)
        return cls._instance

    @classmethod
    def from_device(cls, **kwargs) -> Optional["Camera"]:
        """
        create a Camera from the attached device or None if absent

        Args:
            kwargs: the keyword arguments to construct me with
        """
        camera = cls(**kwargs)
        try:
            import gphoto2 as gp
            camera.device = gp.Camera()
        except Exception as error:
            camera.error = error
        return camera

    def open(self):
        """
        open the camera's device once
        """
        if not self.opened:
            try:
                self.device.init()
                self.config = self.device.get_config()
                self.opened = True
            except Exception as error:
                self.error = error

    def close(self):
        """
        close the camera's device if open
        """
        if self.opened:
            self.device.exit()
            self.opened = False
            
    def set_config(self, key: str, value: object, do_set: bool = False):
        """
        set a single camera configuration value

        Args:
            key: the name of the configuration widget
            value: the value to set
            do_set: when True push the configuration to the device
        """
        self.open()
        self.config.get_child_by_name(key).set_value(value)
        if do_set:
            self.device.set_config(self.config)

    def liveview(self) -> Grid:
        """
        the un-zoomed live view grid
        """
        grid = self.magnify(1)
        return grid

    def magnify(self, level: int) -> Grid:
        """
        switch on live view at the given zoom level and return its grid
        """
        self.set_config("viewfinder", 1)
        self.set_config("eoszoom", str(level), do_set=True)
        file = self.device.capture_preview()
        data = file.get_data_and_size()
        grid = Grid.from_jpeg(data)
        return grid