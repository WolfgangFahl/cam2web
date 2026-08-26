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

## Usage
Serve a gphoto2 camera as MJPEG stream on the default port 8088:
```bash
cam2web -s
```
```
usage: cam2web [-h] [-a] [-d] [--debugLocalPath DEBUGLOCALPATH]
               [--debugPort DEBUGPORT] [--debugRemotePath DEBUGREMOTEPATH]
               [--debugServer DEBUGSERVER] [-f] [-q] [-v] [-V]
               [--apache APACHE] [-c] [-l] [-i INPUT] [-rol] [--host HOST]
               [--port PORT] [-s] [--rotate {0,90,180,270,auto}] [--fps FPS]
```
`--rotate {0,90,180,270,auto}` sets the clockwise display rotation, auto being
EXIF based autorotate of stills; `--fps` limits the live view frame rate;
`--host` and `--port` as for every ngwidgets server.

The served paths are documented as OpenAPI at `/docs`, see
[cam2web.bitplan.com/docs](https://cam2web.bitplan.com/docs).

## Documentation
* [Wiki](https://wiki.bitplan.com/index.php/Cam2web)

## Modules
* `cam.camera` — the `Camera` backend (single kept-open gphoto2 session)
* `cam.camera_grid` — the pixel `Grid` served to the user
* `cam.os_gphoto2` — operating system level claim / reset handling
* `cam.cam2web_cmd` — the CLI starter
