"""Unit tests for ImageDiffer.combine_images()."""
from PIL import Image, ImageChops
import pytest

TOP_MARGIN = 80      # images are pasted at y=80
GAP = 100            # horizontal padding added per image
EXTRA_HEIGHT = 200   # extra canvas height for the label area
LABEL_BAND = (0, 0, None, TOP_MARGIN)  # region above the pasted images


def _open(path):
    img = Image.open(str(path))
    img.load()
    return img


@pytest.fixture
def three_images(make_image):
    a = make_image('first.png', size=(30, 20), color=(255, 0, 0))
    b = make_image('second.png', size=(40, 25), color=(0, 255, 0))
    c = make_image('delta.png', size=(50, 10), color=(0, 0, 255))
    return a, b, c


def test_output_file_is_created(differ, three_images, tmp_path):
    out = tmp_path / 'out.png'
    differ.combine_images(*three_images, diff_percentage=12.5, output_image_file=str(out))
    assert out.is_file()


def test_output_canvas_size(differ, three_images, tmp_path):
    out = tmp_path / 'out.png'
    differ.combine_images(*three_images, diff_percentage=0, output_image_file=str(out))
    img = _open(out)
    assert img.mode == 'RGB'
    assert img.size == (30 + 40 + 50 + 3 * GAP, 25 + EXTRA_HEIGHT)


@pytest.mark.parametrize('count', [1, 2, 3, 4])
def test_canvas_size_scales_with_number_of_images(differ, make_image, tmp_path, count):
    paths = [make_image('img%d.png' % i, size=(10, 10)) for i in range(count)]
    out = tmp_path / 'out.png'
    differ.combine_images(*paths, diff_percentage=1.0, output_image_file=str(out))
    assert _open(out).size == (count * (10 + GAP), 10 + EXTRA_HEIGHT)


def test_images_pasted_side_by_side_at_expected_offsets(differ, three_images, tmp_path):
    out = tmp_path / 'out.png'
    differ.combine_images(*three_images, diff_percentage=5, output_image_file=str(out))
    canvas = _open(out)

    x = 0
    for path in three_images:
        src = _open(path).convert('RGB')
        w, h = src.size
        region = canvas.crop((x, TOP_MARGIN, x + w, TOP_MARGIN + h))
        assert ImageChops.difference(region, src).getbbox() is None, path
        x += w + GAP


def test_gaps_between_images_are_black(differ, three_images, tmp_path):
    out = tmp_path / 'out.png'
    differ.combine_images(*three_images, diff_percentage=5, output_image_file=str(out))
    canvas = _open(out)
    # gap right after the first image (30 px wide) and below the images
    assert canvas.getpixel((30 + GAP // 2, TOP_MARGIN + 5)) == (0, 0, 0)
    assert canvas.getpixel((5, canvas.height - 1)) == (0, 0, 0)


def test_labels_are_drawn_above_images(differ, three_images, tmp_path):
    out = tmp_path / 'out.png'
    differ.combine_images(*three_images, diff_percentage=5, output_image_file=str(out))
    canvas = _open(out)
    x = 0
    for path in three_images:
        w = _open(path).width
        band = canvas.crop((x, 0, x + w + GAP, TOP_MARGIN))
        assert band.getbbox() is not None, 'no label drawn for %s' % path
        x += w + GAP


def test_diff_percentage_only_affects_last_label(differ, three_images, tmp_path):
    out1, out2 = tmp_path / 'o1.png', tmp_path / 'o2.png'
    differ.combine_images(*three_images, diff_percentage=1.23, output_image_file=str(out1))
    differ.combine_images(*three_images, diff_percentage=98.76, output_image_file=str(out2))
    c1, c2 = _open(out1), _open(out2)

    bbox = ImageChops.difference(c1, c2).getbbox()
    assert bbox is not None, 'diff_percentage is not rendered'
    last_image_x = 30 + GAP + 40 + GAP
    assert bbox[0] >= last_image_x          # change is only in the last column
    assert bbox[3] <= TOP_MARGIN            # ... and only in the label band


def test_same_inputs_produce_identical_output(differ, three_images, tmp_path):
    out1, out2 = tmp_path / 'o1.png', tmp_path / 'o2.png'
    differ.combine_images(*three_images, diff_percentage=42, output_image_file=str(out1))
    differ.combine_images(*three_images, diff_percentage=42, output_image_file=str(out2))
    assert ImageChops.difference(_open(out1), _open(out2)).getbbox() is None


def test_accepts_rgba_and_grayscale_inputs(differ, make_image, tmp_path):
    a = make_image('rgba.png', mode='RGBA', color=(10, 20, 30, 255))
    b = make_image('gray.png', mode='L', color=128)
    out = tmp_path / 'out.png'
    differ.combine_images(a, b, diff_percentage=0, output_image_file=str(out))
    assert _open(out).size == (2 * (10 + GAP), 10 + EXTRA_HEIGHT)


def test_font_resolved_independently_of_cwd(differ, three_images, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / 'out.png'
    differ.combine_images(*three_images, diff_percentage=1, output_image_file=str(out))
    assert out.is_file()


def test_works_with_real_test_images(differ, test_data_dir, tmp_path):
    a = str(test_data_dir / 'original.png')
    b = str(test_data_dir / '50perc.png')
    delta = tmp_path / 'delta.png'
    pct = differ.image_diff(a, b, delta_image_file=str(delta))
    out = tmp_path / 'combined.png'
    differ.combine_images(a, b, str(delta), diff_percentage=pct, output_image_file=str(out))
    assert _open(out).size == (3 * (800 + GAP), 600 + EXTRA_HEIGHT)


def test_missing_input_raises_file_not_found(differ, make_image, tmp_path):
    a = make_image('a.png')
    with pytest.raises(FileNotFoundError):
        differ.combine_images(a, str(tmp_path / 'missing.png'),
                              diff_percentage=0, output_image_file=str(tmp_path / 'out.png'))


def test_diff_percentage_is_keyword_only(differ, make_image, tmp_path):
    a = make_image('a.png')
    with pytest.raises(TypeError):
        differ.combine_images(a, a)  # missing required keyword-only args
