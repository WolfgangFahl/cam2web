"""
Created on 2026-08-23

tests for the camera_grid module

see
https://github.com/WolfgangFahl/scan2wiki/issues/38
https://github.com/WolfgangFahl/scan2wiki/issues/39
https://github.com/WolfgangFahl/scan2wiki/issues/41

@author: wf
"""

from ngwidgets.basetest import Basetest

from cam.camera_grid import Grid


class TestGrid(Basetest):
    """
    test the standard grid coordinate handling
    """

    def setUp(self):
        """
        setUp the test environment
        """
        Basetest.setUp(self, debug=True, profile=True)
