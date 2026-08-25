"""
Created on 2026-08-24

@author: wf
"""

from dataclasses import dataclass

import cam


@dataclass
class Version(object):
    """
    Version handling for cam2web
    """

    name = "cam2web"
    version = cam.__version__
    description = "gphoto2 camera web interface"
    date = "2026-08-20"
    updated = "2026-08-25"

    authors = "Wolfgang Fahl"

    doc_url = "https://wiki.bitplan.com/index.php/Cam2web"
    chat_url = "https://github.com/WolfgangFahl/cam2web/discussions"
    cm_url = "https://github.com/WolfgangFahl/cam2web"

    license = f"""Copyright 2026 contributors. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied."""

    longDescription = f"""{name} version {version}
{description}

  Created by {authors} on {date} last updated {updated}"""
