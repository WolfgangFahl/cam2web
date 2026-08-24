# cam2web

gphoto2 camera web interface

| | |
| :--- | :--- |
| **PyPi** | [![PyPI Status](https://img.shields.io/pypi/v/cam2web.svg)](https://pypi.python.org/pypi/cam2web/) [![License](https://img.shields.io/github/license/WolfgangFahl/cam2web.svg)](https://www.apache.org/licenses/LICENSE-2.0) [![pypi](https://img.shields.io/pypi/pyversions/cam2web)](https://pypi.org/project/cam2web/) [![format](https://img.shields.io/pypi/format/cam2web)](https://pypi.org/project/cam2web/) [![downloads](https://img.shields.io/pypi/dd/cam2web)](https://pypi.org/project/cam2web/) |
| **GitHub** | [![Github Actions Build](https://github.com/WolfgangFahl/cam2web/actions/workflows/build.yml/badge.svg)](https://github.com/WolfgangFahl/cam2web/actions/workflows/build.yml) [![Release](https://img.shields.io/github/v/release/WolfgangFahl/cam2web)](https://github.com/WolfgangFahl/cam2web/releases) [![Contributors](https://img.shields.io/github/contributors/WolfgangFahl/cam2web)](https://github.com/WolfgangFahl/cam2web/graphs/contributors) [![Last Commit](https://img.shields.io/github/last-commit/WolfgangFahl/cam2web)](https://github.com/WolfgangFahl/cam2web/commits/) [![GitHub issues](https://img.shields.io/github/issues/WolfgangFahl/cam2web.svg)](https://github.com/WolfgangFahl/cam2web/issues) [![GitHub closed issues](https://img.shields.io/github/issues-closed/WolfgangFahl/cam2web.svg)](https://github.com/WolfgangFahl/cam2web/issues/?q=is%3Aissue+is%3Aclosed) |
| **Code** | [![style-black](https://img.shields.io/badge/%20style-black-000000.svg)](https://github.com/psf/black) [![imports-isort](https://img.shields.io/badge/%20imports-isort-%231674b1)](https://pycqa.github.io/isort/) |
| **Docs** | [![API Docs](https://img.shields.io/badge/API-Documentation-blue)](https://WolfgangFahl.github.io/cam2web/) [![formatter-docformatter](https://img.shields.io/badge/%20formatter-docformatter-fedcba.svg)](https://github.com/PyCQA/docformatter) [![style-google](https://img.shields.io/badge/%20style-google-3666d6.svg)](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings) |

Live view, focus and capture for a gphoto2 attached camera, served over the web.
Extracted from [scan2wiki](https://github.com/WolfgangFahl/scan2wiki).

## Documentation
* [Wiki](https://wiki.bitplan.com/index.php/Cam2web)

## Modules
* `cam.camera` — the `Camera` backend (single kept-open gphoto2 session)
* `cam.camera_grid` — the pixel `Grid` served to the user
* `cam.os_gphoto2` — operating system level claim / reset handling
* `cam.cam2web_cmd` — the CLI starter
