"""Shared pytest fixtures for the image_differ test suite.

Most tests use small synthetic images generated on the fly so that the expected
pixel difference is known exactly. The checked-in images under tests/testdata are
used for the regression tests.
"""
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

# Make the project root importable (image_differ.py lives there, not in a package).
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from image_differ import ImageDiffer  # noqa: E402

TEST_DATA_DIR = ROOT_DIR / 'tests' / 'testdata'
SCRIPT_PATH = ROOT_DIR / 'image_differ.py'
CLI_DELTA_FILE = ROOT_DIR / 'tmp_delta_image.png'


@pytest.fixture
def differ():
    return ImageDiffer()


@pytest.fixture
def test_data_dir():
    return TEST_DATA_DIR


@pytest.fixture
def make_image(tmp_path):
    """Factory that writes a synthetic image to tmp_path and returns its path.

    make_image('a.png', size=(10, 10), color=(0, 0, 0), mode='RGB',
               pixels={(x, y): colour, ...})
    """
    def _make(name, size=(10, 10), color=(0, 0, 0), mode='RGB', pixels=None):
        img = Image.new(mode, size, color)
        for xy, value in (pixels or {}).items():
            img.putpixel(xy, value)
        path = tmp_path / name
        img.save(str(path))
        return str(path)
    return _make


@pytest.fixture
def isolated_cli_delta_file():
    """The CLI always writes tmp_delta_image.png next to image_differ.py.

    Back up any existing file, start each test without one, and restore the
    original state afterwards so CLI tests don't leak into each other or the repo.
    """
    backup = None
    if CLI_DELTA_FILE.exists():
        backup = CLI_DELTA_FILE.read_bytes()
        CLI_DELTA_FILE.unlink()
    yield CLI_DELTA_FILE
    if CLI_DELTA_FILE.exists():
        CLI_DELTA_FILE.unlink()
    if backup is not None:
        CLI_DELTA_FILE.write_bytes(backup)
