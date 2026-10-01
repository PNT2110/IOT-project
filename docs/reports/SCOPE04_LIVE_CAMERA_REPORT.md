# SCOPE-04 Live Camera Report

Evidence class: `VERIFIED_ON_PI`, transient only.

```text
CAMERA_DEVICE=/dev/video0
CAMERA_METADATA_NODE=/dev/video1 (not used as capture)
CAMERA_PROBE=PASS
CAMERA_LIVE_TRANSIENT_FRAME=PASS
CAMERA_FRAME_CONTENT_TYPE=image/jpeg
CAMERA_FRAME_SIZE_BYTES=69689 (bounded in memory; exact smoke sample)
CAMERA_DISCONNECT_CLEAN=PASS
CAMERA_UNAVAILABLE_TYPED_STATE=PASS (DEVICE_UNAVAILABLE on /dev/video99)
CAMERA_RECORDING=NO
CAMERA_FRAME_PERSISTENCE=NO
CAMERA_PERMISSION_CHANGE=NO
CAMERA_GROUP_CHANGE=NO
```

The adapter used `v4l2-ctl` single-frame mmap output captured in process
memory. No image or video file was written. The authenticated AP smoke also
returned `200 image/jpeg` with a transient frame; the frame was discarded.
