# Validation — 2026-10-31

- Python 3.11.11, PyTorch 2.15.0, Pillow 13.0.0, NumPy 2.4.6 on macOS ARM64.
- `python -m pytest -q`: 29 passed.
- `python -m compileall -q watermark.py __init__.py`: passed.
- Independent source/workflow review found a float64 precision issue in unpainted
  gaps inside the overlay ROI. Regression failed before fix and passed afterward.
- Rendered and visually inspected examples/preview.png: Vietnamese accents,
  two-line alignment, shadow, stroke and bottom-right placement.
- Apple MPS smoke run: returned tensor retains MPS device and image dimensions.
- Isolated custom-node package import and widget-based invocation pass.
- Both workflow JSONs checked for matching links, slots and watermark parameters;
  video audio/FPS source connections checked against current ComfyUI source.

Limitations: no live ComfyUI frontend/backend was installed for end-to-end queue
execution. CUDA/ROCm and Windows/Linux execution were not tested locally. CI is
included but has not run remotely. Core video decoding/encoding is delegated to
ComfyUI, not exercised by the unit suite. Published to https://github.com/troubleman2107/ComfyUI-Watermask on branch main.
The full 29-test suite was rerun successfully before the initial push.
