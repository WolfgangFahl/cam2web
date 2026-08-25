"""
Created on 2026-08-24

gphoto2 - operating system level gphoto2 camera / USB claim handling

@author: wf
"""

import sys
import time
from typing import Optional

from basemkit.shell import Shell


class OsGPhoto2:
    """
    operating system level recovery for the gphoto2 camera - frees the
    USB device from claiming daemons and resets a wedged session
    """

    # daemons that claim the PTP device per platform
    daemons = {
        "darwin": "ptpcamerad",
        "linux": "gvfsd-gphoto2",
    }

    # command line tools this module shells out to
    needed_software = ["gphoto2", "killall", "pgrep"]

    def __init__(self):
        """
        construct me
        """
        self.shell = Shell()
        self.error: Optional[Exception] = None

    def __str__(self) -> str:
        """
        show the operating system and its claiming daemon
        """
        daemon = self.daemons.get(sys.platform, "none")
        text = f"OsGPhoto2 on {sys.platform} (daemon: {daemon})"
        return text

    def version(self) -> str:
        """
        the installed gphoto2 version line
        """
        r = self.shell.run("gphoto2 --version", debug=False)
        lines = (r.stdout or "").splitlines()
        version = lines[0].strip() if lines else ""
        return version

    def check_needed_software(self) -> None:
        """
        check the needed command line tools are on the PATH and record
        the first missing one in self.error
        """
        self.error = None
        for tool in self.needed_software:
            r = self.shell.run(f"which {tool}", debug=False)
            if r.returncode != 0:
                self.error = Exception(f"missing needed software: {tool}")
                return

    def free(self, timeout: float = 1.0) -> None:
        """
        kill the OS daemon that claims the camera and wait until it is
        gone so gphoto2 can claim the device

        Args:
            timeout: seconds to wait for the daemon to disappear
        """
        daemon = self.daemons.get(sys.platform)
        if daemon is None:
            return
        self.shell.run(f"killall -9 {daemon}", debug=False)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.shell.run(f"pgrep -x {daemon}", debug=False)
            if r.returncode != 0:
                return
            # 20 checks per sec
            time.sleep(1 / 20.0)
