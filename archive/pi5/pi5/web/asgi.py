"""ASGI entry point for the approved local SCOPE-04 runtime.

The default is loopback-only. A deployment operator must pass a reviewed
``PiWebConfig`` or invoke uvicorn with an explicitly approved bind address;
this module never starts a listener during import.
"""

import os

from .app import PiWebConfig, create_pi_app
from .camera import V4L2CameraAdapter

camera_device = os.environ.get("SCOPE04_CAMERA_DEVICE", "/dev/video0")
app = create_pi_app(PiWebConfig(camera_device=camera_device), camera=V4L2CameraAdapter(camera_device))
