# Text Watermark Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, task by task.

**Goal:** Deliver an installable text watermark custom node for image/video frames.
**Architecture:** Pillow renders reusable text; torch blends the affected rectangle.
**Tech Stack:** Python >=3.10, Pillow >=10.1, numpy, existing ComfyUI torch.
**Spec:** ../specs/2026-10-31-watermark-design.md

## Global Constraints
- BHWC RGB/RGBA floating tensors; retain shape, dtype and device; no input mutation.
- Bundle Vietnamese-capable font with license; no runtime downloads.
- Push only package content to user-specified repo once URL is available.

## Review Focus
- Transparent input: proper source-over rather than darkened glyph colors.
- Empty/disabled text: exactly unchanged input.
- Long/multiline accented text: fit within image when auto-fit is enabled.
- Invalid color/font/input: helpful error instead of silent fallback.
- Video batch: all frames receive text; original pixels outside overlay untouched.

### Task 1: Renderer and node
Files: watermark.py, __init__.py, fonts/, tests/test_watermark.py, requirements.txt.
Interface: TextWatermark.apply(images, text, font, font_size, color, opacity,
position, margin, offset_x, offset_y, stroke_width, stroke_color,
shadow, shadow_color, shadow_x, shadow_y, line_spacing, alignment, fit_text,
font_path='') -> (IMAGE,).
- [x] Write tests for RGB batch, exact outside pixels, RGBA, anchors, font/size/color,
  opacity, shadow/outline, empty text, auto-fit, invalid input and isolated import.
- [x] Run pytest, confirm missing implementation fails.
- [x] Implement node and registration; bundle font/license.
- [x] Run full pytest suite and commit source.

### Task 2: Delivery
Files: README.md, examples/*, .github/workflows/tests.yml.
Consumes: Task 1 node schema. Produces: image/video workflows and installable ZIP.
- [x] Generate workflows with IMAGE and original audio/FPS connections.
- [x] Verify node dispatch from workflow widget defaults and link consistency.
- [x] Render sample output, inspect image; run full suite and compile check.
- [x] Review complete diff, fix material findings, commit and package tracked files.
- [x] Push to https://github.com/troubleman2107/ComfyUI-Watermask, branch main.
