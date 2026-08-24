"""
Created on 2026-08-24

tests for the gphoto2 module

@author: wf
"""

import unittest

from ngwidgets.basetest import Basetest

from cam.os_gphoto2 import OsGPhoto2


class TestOsGPhoto2(Basetest):
    """
    test the operating system level gphoto2 camera handling
    """

    def setUp(self):
        """
        setUp the test environment
        """
        Basetest.setUp(self, debug=True, profile=True)
        self.gphoto2 = OsGPhoto2()

    def test_needed_software(self):
        """
        test the needed software is available
        """
        if self.debug:
            print(self.gphoto2)
        self.gphoto2.check_needed_software()
        self.assertIsNone(self.gphoto2.error)

    def test_version(self):
        """
        test the installed gphoto2 version is reported
        """
        version = self.gphoto2.version()
        if self.debug:
            print(version)
        self.assertTrue(version.startswith("gphoto2"))

    @unittest.skipIf(Basetest.inPublicCI(), "destructive - real machine only")
    def test_free(self):
        """
        free the camera from its claiming daemon
        """
        self.gphoto2.free()
