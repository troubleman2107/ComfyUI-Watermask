"""Text watermark for ComfyUI IMAGE batches (including decoded video frames)."""
from pathlib import Path
import math

from PIL import Image, ImageColor, ImageDraw, ImageFont
import torch

FONT_DIR = Path(__file__).resolve().parent / 'fonts'
POSITIONS = ['bottom-right', 'bottom-left', 'bottom-center', 'top-left',
             'top-center', 'top-right', 'center-left', 'center', 'center-right']


def available_fonts():
    return sorted(p.relative_to(FONT_DIR).as_posix() for p in FONT_DIR.rglob('*')
                  if p.is_file() and p.suffix.lower() in {'.ttf', '.otf'})


def resolve_font(font, font_path=''):
    path = Path(font_path).expanduser() if font_path.strip() else FONT_DIR / font
    if not path.is_file() or path.suffix.lower() not in {'.ttf', '.otf'}:
        raise ValueError(f'Font not found or not TTF/OTF: {path}. Add a font to fonts/ or set font_path.')
    return path


def parse_color(value):
    try:
        color = ImageColor.getrgb(value.strip())
        if len(color) != 3:
            raise ValueError('Use opacity for transparency')
        return color + (255,)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f'Invalid color {value!r}. Use #RRGGBB or a color name, e.g. white.') from exc


class TextWatermark:
    CATEGORY = 'image/watermark'
    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('images',)
    FUNCTION = 'apply'
    DESCRIPTION = 'Text watermark for RGB/RGBA images and video frame batches. Audio and FPS bypass this node.'

    @classmethod
    def INPUT_TYPES(cls):
        fonts = available_fonts()
        return {'required': {
            'images': ('IMAGE',),
            'text': ('STRING', {'default': 'Bản quyền © Studio', 'multiline': True}),
            'font': (fonts, {'default': 'NotoSans.ttf'}),
            'font_size': ('INT', {'default': 36, 'min': 1, 'max': 1024}),
            'color': ('STRING', {'default': '#FFFFFF'}),
            'opacity': ('FLOAT', {'default': .85, 'min': 0, 'max': 1, 'step': .01}),
            'position': (POSITIONS,),
            'margin': ('INT', {'default': 24, 'min': 0, 'max': 8192}),
            'offset_x': ('INT', {'default': 0, 'min': -16384, 'max': 16384}),
            'offset_y': ('INT', {'default': 0, 'min': -16384, 'max': 16384}),
            'stroke_width': ('INT', {'default': 2, 'min': 0, 'max': 64}),
            'stroke_color': ('STRING', {'default': '#000000'}),
            'shadow': ('BOOLEAN', {'default': True}),
            'shadow_color': ('STRING', {'default': '#000000'}),
            'shadow_x': ('INT', {'default': 3, 'min': -256, 'max': 256}),
            'shadow_y': ('INT', {'default': 3, 'min': -256, 'max': 256}),
            'line_spacing': ('INT', {'default': 4, 'min': 0, 'max': 256}),
            'alignment': (['left', 'center', 'right'],),
            'fit_text': ('BOOLEAN', {'default': True}),
        }, 'optional': {
            'font_path': ('STRING', {'default': '', 'tooltip': 'Optional absolute font path on the ComfyUI server. Overrides font dropdown.'}),
        }}

    @classmethod
    def IS_CHANGED(cls, font='NotoSans.ttf', font_path='', **kwargs):
        # ComfyUI already fingerprints all widget inputs. Include font file changes.
        try:
            path = resolve_font(font, font_path)
            info = path.stat()
            return (str(path.resolve()), info.st_mtime_ns, info.st_size)
        except ValueError:
            return float('nan')

    def apply(self, images, text, font='NotoSans.ttf', font_size=36,
              color='#FFFFFF', opacity=.85, position='bottom-right', margin=24,
              offset_x=0, offset_y=0, stroke_width=2, stroke_color='#000000',
              shadow=True, shadow_color='#000000', shadow_x=3, shadow_y=3,
              line_spacing=4, alignment='left', fit_text=True, font_path=''):
        if (not isinstance(images, torch.Tensor) or images.ndim != 4
                or images.shape[-1] not in (3, 4) or not images.is_floating_point()
                or images.shape[1] < 1 or images.shape[2] < 1):
            raise ValueError('images must be a floating IMAGE tensor [batch, height, width, 3 or 4].')
        if not math.isfinite(opacity) or not 0 <= opacity <= 1:
            raise ValueError('opacity must be between 0 and 1.')
        for key, value, low, high in [
            ('font_size', font_size, 1, 1024), ('margin', margin, 0, 8192),
            ('stroke_width', stroke_width, 0, 64), ('line_spacing', line_spacing, 0, 256),
            ('offset_x', offset_x, -16384, 16384), ('offset_y', offset_y, -16384, 16384),
            ('shadow_x', shadow_x, -256, 256), ('shadow_y', shadow_y, -256, 256),
        ]:
            if not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f'{key} must be an integer in [{low}, {high}].')
        if position not in POSITIONS or alignment not in ('left', 'center', 'right'):
            raise ValueError('Invalid position or alignment.')
        if not isinstance(text, str) or len(text) > 10000:
            raise ValueError('text must be a string of at most 10000 characters.')
        if images.shape[0] == 0 or not text.strip() or opacity == 0:
            return (images,)

        fill, outline, shade = map(parse_color, (color, stroke_color, shadow_color))
        path = resolve_font(font, font_path)
        _, height, width, channels = images.shape
        measure = ImageDraw.Draw(Image.new('L', (1, 1)))

        def layout(size):
            try:
                face = ImageFont.truetype(str(path), size)
            except OSError as exc:
                raise ValueError(f'Cannot load font: {path}') from exc
            bounds = measure.multiline_textbbox((0, 0), text, font=face,
                      spacing=line_spacing, align=alignment, stroke_width=stroke_width)
            left, top, right, bottom = bounds
            if shadow:
                left += min(0, shadow_x)
                top += min(0, shadow_y)
                right += max(0, shadow_x)
                bottom += max(0, shadow_y)
            return face, (math.floor(left), math.floor(top), math.ceil(right), math.ceil(bottom))

        # Keep a nonempty drawable area even for thumbnails smaller than the margin.
        mx, my = min(margin, (width - 1) // 2), min(margin, (height - 1) // 2)
        face, bounds = layout(font_size)
        if fit_text:
            lo, hi = 1, font_size
            while lo < hi:
                mid = (lo + hi + 1) // 2
                _, box = layout(mid)
                if box[2] - box[0] <= width - 2 * mx and box[3] - box[1] <= height - 2 * my:
                    lo = mid
                else:
                    hi = mid - 1
            face, bounds = layout(lo)
        left, top, right, bottom = bounds
        tw, th = right - left, bottom - top
        horizontal = position.split('-')[-1]
        vertical = position.split('-')[0]
        x = mx if horizontal == 'left' else width - mx - tw if horizontal == 'right' else (width - tw) // 2
        y = my if vertical == 'top' else height - my - th if vertical == 'bottom' else (height - th) // 2
        origin = (x - left + offset_x, y - top + offset_y)
        layer = Image.new('RGBA', (width, height))
        draw_args = dict(font=face, spacing=line_spacing, align=alignment, stroke_width=stroke_width)
        if shadow:
            ImageDraw.Draw(layer).multiline_text((origin[0] + shadow_x, origin[1] + shadow_y),
                text, fill=shade, stroke_fill=shade, **draw_args)
        foreground = Image.new('RGBA', (width, height))
        ImageDraw.Draw(foreground).multiline_text(origin, text, fill=fill, stroke_fill=outline, **draw_args)
        layer = Image.alpha_composite(layer, foreground)
        roi = layer.getbbox()
        if roi is None:
            return (images,)
        x0, y0, x1, y1 = roi
        # Render once, reuse for every frame; never quantize the source image to uint8.
        pixels = bytearray(layer.crop(roi).tobytes())
        overlay = torch.frombuffer(pixels, dtype=torch.uint8).reshape(y1 - y0, x1 - x0, 4)
        overlay = overlay.to(device=images.device, dtype=torch.float32).div_(255)
        src_rgb = overlay[..., :3]
        src_a = overlay[..., 3:4] * opacity
        result = images.clone()
        for index in range(images.shape[0]):
            base = images[index, y0:y1, x0:x1].to(torch.float32)
            if channels == 3:
                mixed = src_rgb * src_a + base * (1 - src_a)
            else:
                alpha = src_a + base[..., 3:4] * (1 - src_a)
                premultiplied = src_rgb * src_a + base[..., :3] * base[..., 3:4] * (1 - src_a)
                rgb = premultiplied / alpha.clamp_min(torch.finfo(torch.float32).tiny)
                mixed = torch.cat((rgb, alpha), dim=-1)
            # Includes transparent gaps inside a multiline bounding rectangle.
            result[index, y0:y1, x0:x1] = torch.where(
                src_a > 0, mixed.to(images.dtype), images[index, y0:y1, x0:x1]
            )
        return (result,)
