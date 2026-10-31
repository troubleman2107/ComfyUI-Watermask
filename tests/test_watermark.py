import importlib.util
from pathlib import Path
import sys
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from watermark import TextWatermark


def apply(image=None, **kwargs):
    if image is None:
        image = torch.zeros(2, 160, 320, 3)
    return TextWatermark().apply(image, **dict(dict(
        text='Tiếng Việt', font='NotoSans.ttf', font_size=28,
        color='#ff0000', opacity=1.0, position='bottom-right', margin=12,
        offset_x=0, offset_y=0, stroke_width=0, stroke_color='#000000',
        shadow=False, shadow_color='#000000', shadow_x=3, shadow_y=3,
        line_spacing=4, alignment='left', fit_text=True, font_path=''
    ), **kwargs))[0]


def test_batch_color_and_source_unchanged():
    source = torch.rand(3, 160, 320, 3)
    original = source.clone()
    result = apply(source)
    assert torch.equal(source, original)
    assert result.shape == source.shape and result.dtype == source.dtype
    assert torch.equal(result[:, :80], source[:, :80])
    assert all(not torch.equal(result[i], source[i]) for i in range(3))
    red = apply()
    assert red[..., 0].max() == 1
    assert red[..., 1:].max() == 0


@pytest.mark.parametrize('kwargs', [{'text': ''}, {'text': ' \n '}, {'opacity': 0}])
def test_noop_exact(kwargs):
    source = torch.rand(1, 40, 60, 3)
    assert torch.equal(apply(source, **kwargs), source)


def test_opacity():
    assert torch.allclose(apply(opacity=.5), apply() * .5, atol=1e-6)


def test_rgba_source_over_transparent_background():
    source = torch.zeros(1, 160, 320, 4)
    result = apply(source, opacity=.5)
    marked = result[0, ..., 3] > 0
    assert marked.any()
    assert torch.all(result[0, ..., 0][marked] == 1)
    assert torch.all(result[0, ..., 1:3][marked] == 0)
    assert result[..., 3].max() == .5
    assert torch.equal(result[~marked.unsqueeze(0)], source[~marked.unsqueeze(0)])


def test_rgba_semitransparent_source_over():
    source = torch.zeros(1, 160, 320, 4)
    source[..., 2] = 1
    source[..., 3] = .5
    result = apply(source, opacity=.5)
    y, x = torch.nonzero(result[0, ..., 3] == .75)[0]
    assert torch.allclose(result[0, y, x], torch.tensor([2/3, 0, 1/3, .75]))


@pytest.mark.parametrize('position,checks', [
    ('top-left', (0, 0)), ('top-right', (1, 0)),
    ('bottom-left', (0, 1)), ('bottom-right', (1, 1)), ('center', (.5, .5))])
def test_anchor(position, checks):
    result = apply(text='X', position=position)
    ys, xs = torch.where(result[0, ..., 0] > 0)
    cx, cy = float(xs.float().mean()), float(ys.float().mean())
    assert (cx < 80 if checks[0] == 0 else cx > 240 if checks[0] == 1 else 140 < cx < 180)
    assert (cy < 40 if checks[1] == 0 else cy > 120 if checks[1] == 1 else 60 < cy < 100)


def test_font_size_multiline_fit_and_offsets():
    small = apply(text='X', font_size=16)
    large = apply(text='X', font_size=40)
    assert (large > 0).sum() > (small > 0).sum()
    fit = apply(torch.zeros(1, 70, 120, 3), text='Đóng dấu bản quyền\nTiếng Việt', font_size=120, margin=5)
    assert fit.max() > 0
    assert fit[:, :5].max() == 0 and fit[:, -5:].max() == 0
    assert fit[:, :, :5].max() == 0 and fit[:, :, -5:].max() == 0
    shifted = apply(text='X', position='top-left', offset_x=10, offset_y=7)
    base = apply(text='X', position='top-left')
    assert torch.equal(shifted[:, 7:, 10:], base[:, :-7, :-10])


def test_outline_and_shadow_add_pixels():
    plain = apply(text='X', color='white')
    outlined = apply(text='X', color='white', stroke_width=3, stroke_color='blue')
    shadowed = apply(text='X', color='white', shadow=True, shadow_color='blue', shadow_x=10)
    assert (outlined > 0).sum() > (plain > 0).sum()
    assert (shadowed > 0).sum() > (plain > 0).sum()


@pytest.mark.parametrize('kwargs', [
    {'color': 'bad-color'}, {'font': 'missing.ttf'}, {'font_path': '/nonexistent.ttf'},
    {'opacity': 2}, {'font_size': 0}, {'position': 'unknown'},
])
def test_invalid_settings_fail_clearly(kwargs):
    with pytest.raises(ValueError):
        apply(**kwargs)


@pytest.mark.parametrize('shape,dtype', [((1, 2, 3), torch.float32), ((1, 20, 20, 1), torch.float32), ((1, 20, 20, 3), torch.uint8)])
def test_invalid_images(shape, dtype):
    with pytest.raises(ValueError):
        apply(torch.zeros(shape, dtype=dtype))


def test_dtype_empty_batch_and_tiny_canvas():
    source = torch.zeros(1, 40, 80, 3, dtype=torch.float16)
    assert apply(source).dtype == torch.float16
    empty = torch.zeros(0, 40, 80, 3)
    assert apply(empty).shape == empty.shape
    assert apply(torch.zeros(1, 1, 1, 3)).shape == (1, 1, 1, 3)


def test_external_font_and_isolated_package_loading():
    assert torch.equal(apply(), apply(font_path=str(ROOT / 'fonts/NotoSans.ttf')))
    spec = importlib.util.spec_from_file_location('custom_watermark_test', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    cls = module.NODE_CLASS_MAPPINGS['TextWatermark']
    result = cls().apply(torch.zeros(1, 160, 320, 3), **{
        key: (value[0][0] if isinstance(value[0], list) else value[1]['default'])
        for key, value in cls.INPUT_TYPES()['required'].items() if key != 'images'
    })[0]
    assert result.max() > 0


def test_offscreen_clipping_is_noop():
    source = torch.rand(1, 80, 100, 3)
    assert torch.equal(apply(source, offset_x=500), source)


def test_float64_unpainted_pixels_are_exact():
    source = torch.rand(1, 160, 320, 3, dtype=torch.float64)
    coverage = apply(torch.zeros_like(source))[..., 0] > 0
    result = apply(source)
    assert torch.equal(result[~coverage], source[~coverage])


def test_font_file_replacement_changes_cache_key(tmp_path):
    import shutil
    import os
    path = tmp_path / 'custom.ttf'
    shutil.copyfile(ROOT / 'fonts/NotoSans.ttf', path)
    before = TextWatermark.IS_CHANGED(font_path=str(path))
    stamp = path.stat().st_mtime_ns + 1000000
    os.utime(path, ns=(stamp, stamp))
    after = TextWatermark.IS_CHANGED(font_path=str(path))
    assert before != after


def test_example_workflows_have_consistent_links_and_runnable_watermark():
    import json
    for path in (ROOT / 'examples').glob('*.json'):
        workflow = json.loads(path.read_text())
        nodes = {node['id']: node for node in workflow['nodes']}
        for link_id, src, src_slot, dst, dst_slot, kind in workflow['links']:
            assert link_id in nodes[src]['outputs'][src_slot]['links']
            assert nodes[dst]['inputs'][dst_slot]['link'] == link_id
            assert nodes[src]['outputs'][src_slot]['type'] == kind
            assert nodes[dst]['inputs'][dst_slot]['type'] == kind
        watermark = next(n for n in nodes.values() if n['type'] == 'TextWatermark')
        keys = [k for k in TextWatermark.INPUT_TYPES()['required'] if k != 'images'] + ['font_path']
        assert len(watermark['widgets_values']) == len(keys)
        result = TextWatermark().apply(torch.zeros(1, 160, 320, 3), **dict(zip(keys, watermark['widgets_values'])))[0]
        assert result.max() > 0
        if 'video' in path.name:
            create = next(n for n in nodes.values() if n['type'] == 'CreateVideo')
            for name, source_slot in [('audio', 1), ('fps', 2)]:
                inlet = next(i for i in create['inputs'] if i['name'] == name)
                link = next(l for l in workflow['links'] if l[0] == inlet['link'])
                assert nodes[link[1]]['type'] == 'GetVideoComponents'
                assert link[2] == source_slot


def test_node_loads_and_renders_without_numpy(monkeypatch):
    """The node must not force users to upgrade NumPy in older ComfyUI installs."""
    import builtins
    original_import = builtins.__import__

    def without_numpy(name, *args, **kwargs):
        if name == 'numpy' or name.startswith('numpy.'):
            raise ImportError('NumPy deliberately unavailable for this regression test')
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', without_numpy)
    spec = importlib.util.spec_from_file_location('watermark_without_numpy', ROOT / 'watermark.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = torch.zeros(2, 120, 240, 3)
    result = module.TextWatermark().apply(source, text='Tiếng Việt')[0]
    assert result.shape == source.shape
    assert result.max() > 0
    assert torch.equal(result[0], result[1])
    assert source.max() == 0
