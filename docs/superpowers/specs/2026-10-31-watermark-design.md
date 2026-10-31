# Text Watermark

User requested a ComfyUI node to watermark images and videos, editable text,
font, size, color, repo push and installation instructions. User authorized
implementation without further design questions ("cứ triển khai").

Builder choices: a Python legacy-compatible IMAGE node operates on BHWC image
batches, including video frames. Pillow renders an RGBA text layer once; torch
composites only its region on each frame without quantizing original pixels.
Ship an OFL-licensed Noto Sans font for Vietnamese, accept fonts in fonts/ and
an explicit local font path. Support 9 anchors, margins, offsets, opacity,
outline, shadow, multiline alignment and optional shrink-to-fit. Preserve
shape, dtype, device, source tensor, and implement correct RGBA source-over.
No audio or FPS processing inside node: supplied workflow routes those from
GetVideoComponents into CreateVideo. SDR images only; long videos require RAM.

Approaches: direct video decoding would duplicate core codecs/audio handling;
frame-batch processing integrates core video nodes and VHS. Builder selected
frame-batch processing. No web UI extension or external service needed.

Delivery: source, real tensor tests, image and video workflow JSON, Vietnamese
README, installable ZIP, local Git commit. Push requires the user's repo URL;
none has been supplied. Current Blender repo is unrelated and has no remote,
so create a separate package/repository without staging Blender files.
