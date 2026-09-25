"""Unit tests for ImageDiffer.image_diff()."""
import io
import logging
from pathlib import Path

import pytest
from PIL import Image, ImageChops

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


# --------------------------------------------------------------------------- #
# Regression tests against the checked-in test images
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('file1, file2, expected', [
    ('original.png', '25perc.png', 25.14604166666667),
    ('original.png', '50perc.png', 50.29125),
    ('original.png', '75perc.png', 75.14562500000001),
    ('original.png', '100perc.png', 100.0),
    ('complex1.png', 'complex2.png', 1.5638385962700527),
])
def test_known_images_exact_percentage(differ, test_data_dir, file1, file2, expected):
    result = differ.image_diff(str(test_data_dir / file1), str(test_data_dir / file2))
    assert result == pytest.approx(expected)


@pytest.mark.parametrize('name', ['original.png', '25perc.png', 'complex1.png'])
def test_image_compared_with_itself_is_zero(differ, test_data_dir, name):
    path = str(test_data_dir / name)
    assert differ.image_diff(path, path) == 0


@pytest.mark.parametrize('file1, file2', [
    ('original.png', '50perc.png'),
    ('complex1.png', 'complex2.png'),
])
def test_diff_is_symmetric(differ, test_data_dir, file1, file2):
    a, b = str(test_data_dir / file1), str(test_data_dir / file2)
    assert differ.image_diff(a, b) == pytest.approx(differ.image_diff(b, a))


# --------------------------------------------------------------------------- #
# Exact percentage calculation with synthetic images
# --------------------------------------------------------------------------- #
def test_identical_images_return_zero(differ, make_image):
    a = make_image('a.png', color=(12, 34, 56))
    b = make_image('b.png', color=(12, 34, 56))
    assert differ.image_diff(a, b) == 0


def test_completely_different_images_return_100(differ, make_image):
    a = make_image('a.png', color=BLACK)
    b = make_image('b.png', color=WHITE)
    assert differ.image_diff(a, b) == pytest.approx(100.0)


@pytest.mark.parametrize('n_changed', [1, 2, 7, 25, 50, 99])
def test_percentage_matches_number_of_changed_pixels(differ, make_image, n_changed):
    size = (10, 10)
    changed = {(i % 10, i // 10): WHITE for i in range(n_changed)}
    a = make_image('a.png', size=size)
    b = make_image('b.png', size=size, pixels=changed)
    assert differ.image_diff(a, b) == pytest.approx(n_changed)  # 100 px -> 1 px == 1%


def test_percentage_uses_whole_image_not_bounding_box(differ, make_image):
    # Two changed pixels at opposite corners: the bbox is the whole image but only
    # 2 of 400 pixels differ -> 0.5 %.
    size = (20, 20)
    a = make_image('a.png', size=size)
    b = make_image('b.png', size=size, pixels={(0, 0): WHITE, (19, 19): WHITE})
    assert differ.image_diff(a, b) == pytest.approx(0.5)


def test_non_square_image(differ, make_image):
    size = (40, 5)  # 200 px
    a = make_image('a.png', size=size)
    b = make_image('b.png', size=size, pixels={(39, 4): WHITE})
    assert differ.image_diff(a, b) == pytest.approx(0.5)


@pytest.mark.parametrize('changed_color', [
    (1, 0, 0),    # smallest possible change on red
    (0, 1, 0),    # ... green
    (0, 0, 1),    # ... blue (lowest weight in RGB->L conversion)
    (255, 0, 0),
    (0, 0, 255),
])
def test_smallest_single_channel_change_is_detected(differ, make_image, changed_color):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(5, 5): changed_color})
    assert differ.image_diff(a, b) == pytest.approx(1.0)


def test_pixel_counted_once_even_if_all_channels_differ(differ, make_image):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): (10, 20, 30)})
    assert differ.image_diff(a, b) == pytest.approx(1.0)


@pytest.mark.parametrize('mode, bg, fg', [
    ('L', 0, 255),
    ('L', 100, 101),
])
def test_other_image_modes(differ, make_image, mode, bg, fg):
    a = make_image('a.png', mode=mode, color=bg)
    b = make_image('b.png', mode=mode, color=bg, pixels={(3, 3): fg})
    assert differ.image_diff(a, b) == pytest.approx(1.0)


def test_single_pixel_images(differ, make_image):
    a = make_image('a.png', size=(1, 1), color=BLACK)
    b = make_image('b.png', size=(1, 1), color=WHITE)
    assert differ.image_diff(a, b) == pytest.approx(100.0)
    assert differ.image_diff(a, a) == 0


def test_result_is_between_0_and_100(differ, test_data_dir):
    result = differ.image_diff(str(test_data_dir / 'original.png'),
                               str(test_data_dir / '75perc.png'))
    assert 0 <= result <= 100


# --------------------------------------------------------------------------- #
# Input types accepted
# --------------------------------------------------------------------------- #
def test_accepts_pathlib_paths(differ, make_image):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    assert differ.image_diff(Path(a), Path(b)) == pytest.approx(1.0)


def test_accepts_file_like_objects(differ, make_image):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        assert differ.image_diff(io.BytesIO(fa.read()), io.BytesIO(fb.read())) == pytest.approx(1.0)


def test_accepts_keyword_arguments(differ, make_image, tmp_path):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    delta = tmp_path / 'delta.png'
    result = differ.image_diff(input_imgge1_file=a, input_image2_file=b,
                               delta_image_file=str(delta))
    assert result == pytest.approx(1.0)
    assert delta.is_file()


# --------------------------------------------------------------------------- #
# Delta image output
# --------------------------------------------------------------------------- #
def test_delta_image_written_when_images_differ(differ, make_image, tmp_path):
    size = (8, 6)
    a = make_image('a.png', size=size)
    b = make_image('b.png', size=size, pixels={(2, 3): (200, 100, 50)})
    delta = tmp_path / 'delta.png'

    differ.image_diff(a, b, delta_image_file=str(delta))

    assert delta.is_file()
    with Image.open(str(delta)) as img:
        assert img.mode == 'RGB'
        assert img.size == size
        assert img.getpixel((2, 3)) == (200, 100, 50)   # |a - b| per channel
        assert img.getpixel((0, 0)) == BLACK             # unchanged pixel is black
        # exactly one non-black pixel
        assert ImageChops.difference(img, Image.new('RGB', size)).getbbox() == (2, 3, 3, 4)


def test_delta_image_from_rgba_is_saved_as_rgb(differ, make_image, tmp_path):
    a = make_image('a.png', mode='RGBA', color=(0, 0, 0, 255))
    # alpha also changes here so the delta is written despite the RGBA bbox issue below
    b = make_image('b.png', mode='RGBA', color=(0, 0, 0, 255), pixels={(0, 0): (9, 9, 9, 0)})
    delta = tmp_path / 'delta.png'
    differ.image_diff(a, b, delta_image_file=str(delta))
    with Image.open(str(delta)) as img:
        assert img.mode == 'RGB'


def test_delta_image_not_written_when_images_identical(differ, make_image, tmp_path):
    a = make_image('a.png')
    delta = tmp_path / 'delta.png'
    assert differ.image_diff(a, a, delta_image_file=str(delta)) == 0
    assert not delta.exists()


def test_no_delta_image_when_not_requested(differ, make_image, tmp_path):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    before = set(tmp_path.iterdir())
    differ.image_diff(a, b)
    assert set(tmp_path.iterdir()) == before


def test_delta_image_format_follows_extension(differ, make_image, tmp_path):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    delta = tmp_path / 'delta.bmp'
    differ.image_diff(a, b, delta_image_file=str(delta))
    with Image.open(str(delta)) as img:
        assert img.format == 'BMP'


# --------------------------------------------------------------------------- #
# Error handling
# --------------------------------------------------------------------------- #
def test_different_sizes_exit_with_code_2(differ, make_image, caplog):
    a = make_image('a.png', size=(10, 10))
    b = make_image('b.png', size=(10, 11))
    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            differ.image_diff(a, b)
    assert exc.value.code == 2
    assert 'different image size' in caplog.text


def test_different_sizes_does_not_write_delta(differ, make_image, tmp_path):
    a = make_image('a.png', size=(10, 10))
    b = make_image('b.png', size=(11, 10))
    delta = tmp_path / 'delta.png'
    with pytest.raises(SystemExit):
        differ.image_diff(a, b, delta_image_file=str(delta))
    assert not delta.exists()


def test_different_modes_raise_value_error(differ, make_image):
    a = make_image('a.png', mode='RGB', color=BLACK)
    b = make_image('b.png', mode='L', color=0)
    with pytest.raises(ValueError):
        differ.image_diff(a, b)


@pytest.mark.parametrize('which', ['first', 'second'])
def test_missing_file_raises_file_not_found(differ, make_image, tmp_path, which):
    good = make_image('good.png')
    missing = str(tmp_path / 'does_not_exist.png')
    args = (missing, good) if which == 'first' else (good, missing)
    with pytest.raises(FileNotFoundError):
        differ.image_diff(*args)


def test_non_image_file_raises(differ, make_image, tmp_path):
    good = make_image('good.png')
    bogus = tmp_path / 'not_an_image.png'
    bogus.write_text('this is not a png')
    with pytest.raises(Exception):  # PIL.UnidentifiedImageError (an OSError) on modern Pillow
        differ.image_diff(good, str(bogus))


# --------------------------------------------------------------------------- #
# Known issues (documented as expected failures)
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason='Known issue: convert("L") drops the alpha channel, so '
                                       'transparency-only changes are counted as 0%.')
def test_alpha_only_difference_is_counted(differ, make_image):
    a = make_image('a.png', mode='RGBA', color=(0, 0, 0, 255))
    b = make_image('b.png', mode='RGBA', color=(0, 0, 0, 255), pixels={(0, 0): (0, 0, 0, 0)})
    assert differ.image_diff(a, b) == pytest.approx(1.0)


@pytest.mark.xfail(strict=True, reason='Known issue: for RGBA images Image.getbbox() only looks at the '
                                       'alpha band, so colour changes in opaque RGBA images (e.g. most '
                                       'PNG screenshots) are reported as 0% with no delta image.')
@pytest.mark.parametrize('changed', [(0, 0, 1, 255), (255, 255, 255, 255)])
def test_rgba_colour_difference_is_counted(differ, make_image, changed):
    a = make_image('a.png', mode='RGBA', color=(0, 0, 0, 255))
    b = make_image('b.png', mode='RGBA', color=(0, 0, 0, 255), pixels={(3, 3): changed})
    assert differ.image_diff(a, b) == pytest.approx(1.0)


@pytest.mark.xfail(strict=True, reason='Known issue: fully different opaque RGBA images report 0%.')
def test_rgba_black_vs_white_is_100_percent(differ, make_image):
    a = make_image('a.png', mode='RGBA', color=(0, 0, 0, 255))
    b = make_image('b.png', mode='RGBA', color=(255, 255, 255, 255))
    assert differ.image_diff(a, b) == pytest.approx(100.0)
