"""
Created on 2026-08-20

camera - camera handling of cam2web
see https://github.com/WolfgangFahl/scan2wiki/issues/33

@author: wf
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
    config: Optional[Any] = None
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

    def summary(self) -> str:
        """
        the gphoto2 summary of my device

        Returns:
            the summary text
        """
        self.open()
        summary = self.device.get_summary().text if self.device is not None else "N/A"
        return summary

    def state(self) -> dict:
        """
        my device level state

        Returns:
            the device state as a dict
        """
        state = {
            "present": self.device is not None,
            "open": self.opened,
        }
        return state

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

        Raises:
            ValueError: if the camera could not be opened
        """
        self.open()
        if self.config is None:
            raise ValueError(f"camera is not open: {self.error}")
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

        Args:
            level: the zoom level - 1 is the full view

        Returns:
            the Grid of the captured preview frame
        """
        self.start_liveview(level)
        data = self.preview()
        grid = Grid.from_jpeg(data, zoom=level)
        return grid

    def start_liveview(self, level: int = 1, position: Optional[str] = None) -> None:
        """
        switch my device to live view at the given zoom level

        Args:
            level: the zoom level - 1 is the full view
            position: the eoszoomposition as "x,y" in sensor pixels
        """
        self.set_config("viewfinder", 1)
        self.set_zoom_level(level)
        if position is not None:
            self.set_zoom_position(position)

    def set_zoom_level(self, level: int) -> None:
        """
        set the zoom level of a running live view

        the device needs a moment and a frame to follow, so zoom and
        position are set one after the other and not per mouse move

        Args:
            level: the zoom level - 1 is the full view
        """
        self.set_config("eoszoom", str(level), do_set=True)

    def set_zoom_position(self, position: str) -> None:
        """
        set the magnified area of a running live view

        Args:
            position: the eoszoomposition as "x,y" in sensor pixels
        """
        self.set_config("eoszoomposition", position, do_set=True)

    def stop_liveview(self) -> None:
        """
        switch my device's live view off
        """
        self.set_config("viewfinder", 0, do_set=True)

    def preview(self) -> bytes:
        """
        one live view frame - live view has to be started first

        Returns:
            the JPEG data of the frame
        """
        file = self.device.capture_preview()
        data = bytes(file.get_data_and_size())
        return data
