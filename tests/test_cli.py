"""Tests for the command-line entry point (the ``if __name__ == "__main__"`` block).

The script is executed in-process with runpy so that coverage tools see it.
Note: the CLI always writes tmp_delta_image.png next to image_differ.py; the
``isolated_cli_delta_file`` fixture cleans that up. Run these tests serially
(or with ``pytest -n auto --dist loadfile``) because they share that file.
"""
import logging
import os
import runpy
import sys

import pytest
from PIL import Image

from conftest import SCRIPT_PATH

WHITE = (255, 255, 255)

pytestmark = pytest.mark.usefixtures('isolated_cli_delta_file')


def run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, 'argv', ['image_differ.py'] + [str(a) for a in args])
    runpy.run_path(str(SCRIPT_PATH), run_name='__main__')


@pytest.fixture
def cli_log(caplog):
    caplog.set_level(logging.INFO)
    return caplog


# --------------------------------------------------------------------------- #
# Argument validation
# --------------------------------------------------------------------------- #
def test_help_exits_cleanly(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, '--help')
    assert exc.value.code == 0
    assert '--input_image1_file' in capsys.readouterr().out


@pytest.mark.parametrize('args', [
    [],
    ['--input_image1_file', 'a.png'],
    ['--input_image2_file', 'b.png'],
])
def test_missing_required_arguments(monkeypatch, capsys, args):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, *args)
    assert exc.value.code == 2
    assert 'required' in capsys.readouterr().err


def test_missing_first_input_file(monkeypatch, make_image, tmp_path, cli_log):
    good = make_image('good.png')
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, '--input_image1_file', tmp_path / 'nope.png',
                '--input_image2_file', good)
    assert exc.value.code == 1
    assert 'input_image1_file' in cli_log.text and 'does not exist' in cli_log.text


def test_missing_second_input_file(monkeypatch, make_image, tmp_path, cli_log):
    good = make_image('good.png')
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, '--input_image1_file', good,
                '--input_image2_file', tmp_path / 'nope.png')
    assert exc.value.code == 1
    assert 'input_image2_file' in cli_log.text and 'does not exist' in cli_log.text


def test_input_path_is_directory(monkeypatch, make_image, tmp_path, cli_log):
    good = make_image('good.png')
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, '--input_image1_file', tmp_path, '--input_image2_file', good)
    assert exc.value.code == 1


# --------------------------------------------------------------------------- #
# Happy paths
# --------------------------------------------------------------------------- #
def test_reports_percentage_without_output_file(monkeypatch, make_image, cli_log):
    a = make_image('a.png', size=(4, 1))
    b = make_image('b.png', size=(4, 1), pixels={(0, 0): WHITE})
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b)
    assert 'Percentage difference between the two images: 25%' in cli_log.text
    assert 'output file has been saved' not in cli_log.text


def test_writes_delta_image_next_to_script(monkeypatch, make_image, isolated_cli_delta_file):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b)
    assert isolated_cli_delta_file.is_file()


def test_writes_combined_output_image(monkeypatch, make_image, tmp_path, cli_log):
    a = make_image('a.png', size=(20, 10))
    b = make_image('b.png', size=(20, 10), pixels={(0, 0): WHITE})
    out = tmp_path / 'combined.png'
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b,
            '--output_image_file', out)
    assert out.is_file()
    with Image.open(str(out)) as img:
        assert img.size == (3 * (20 + 100), 10 + 200)
    assert 'output file has been saved' in cli_log.text


def test_real_test_images(monkeypatch, test_data_dir, tmp_path, cli_log):
    out = tmp_path / 'combined.png'
    run_cli(monkeypatch,
            '--input_image1_file', test_data_dir / 'original.png',
            '--input_image2_file', test_data_dir / '75perc.png',
            '--output_image_file', out)
    assert 'Percentage difference between the two images: 75%' in cli_log.text
    assert out.is_file()


# --------------------------------------------------------------------------- #
# Error branches
# --------------------------------------------------------------------------- #
def test_different_image_sizes_exit_with_code_2(monkeypatch, make_image, cli_log):
    a = make_image('a.png', size=(10, 10))
    b = make_image('b.png', size=(20, 10))
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b)
    assert exc.value.code == 2
    assert 'different image size' in cli_log.text


def test_unexpected_exception_is_logged_not_raised(monkeypatch, make_image, cli_log):
    a = make_image('a.png', mode='RGB')
    b = make_image('b.png', mode='L', color=0)   # mode mismatch -> ValueError
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b)
    assert 'Traceback' in cli_log.text
    assert 'ValueError' in cli_log.text


def test_reports_failure_when_output_not_created(monkeypatch, make_image, tmp_path, cli_log):
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    out = str(tmp_path / 'combined.png')

    real_isfile = os.path.isfile
    monkeypatch.setattr(os.path, 'isfile', lambda p: False if str(p) == out else real_isfile(p))
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b,
            '--output_image_file', out)
    assert 'Failed to save output file' in cli_log.text


def test_identical_images_with_output_logs_missing_delta(monkeypatch, make_image, tmp_path, cli_log):
    """Current behaviour: no delta image is written for identical images, so
    combine_images() fails with FileNotFoundError, which the CLI only logs."""
    a = make_image('a.png')
    out = tmp_path / 'combined.png'
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', a,
            '--output_image_file', out)
    assert 'Percentage difference between the two images: 0%' in cli_log.text
    assert 'tmp_delta_image.png' in cli_log.text
    assert not out.exists()


# --------------------------------------------------------------------------- #
# Known issues (documented as expected failures)
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason='Known issue: identical images produce no delta image, '
                                       'so --output_image_file is never written.')
def test_identical_images_still_produce_output(monkeypatch, make_image, tmp_path):
    a = make_image('a.png')
    out = tmp_path / 'combined.png'
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', a,
            '--output_image_file', out)
    assert out.is_file()


@pytest.mark.xfail(strict=True, reason='Known issue: a stale tmp_delta_image.png from a previous '
                                       'run is reused when the current images are identical.')
def test_stale_delta_image_is_not_reused(monkeypatch, make_image, tmp_path, isolated_cli_delta_file):
    # Previous run with different images leaves a delta behind...
    a = make_image('a.png')
    b = make_image('b.png', pixels={(0, 0): WHITE})
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b)
    assert isolated_cli_delta_file.is_file()

    # ...then identical images are compared with an output file requested.
    out = tmp_path / 'combined.png'
    run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', a,
            '--output_image_file', out)
    with Image.open(str(out)) as img:
        delta_region = img.crop((2 * (10 + 100), 80, 2 * (10 + 100) + 10, 90))
        assert delta_region.getbbox() is None, 'stale delta from previous run was used'


@pytest.mark.xfail(strict=True, reason='Known issue: unexpected errors are logged at INFO level and '
                                       'the process exits with status 0.')
def test_unexpected_exception_signals_failure(monkeypatch, make_image):
    a = make_image('a.png', mode='RGB')
    b = make_image('b.png', mode='L', color=0)
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, '--input_image1_file', a, '--input_image2_file', b)
    assert exc.value.code != 0
