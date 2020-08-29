#########################################################################################
# A Python script that performs a quick unit test for the image_diff() function.
# All test images are resided under the tests/testdata directory.
#
# By Ken Chu, kenchu2000@gmail.com
#
#########################################################################################
import pytest
import sys
from pathlib import Path
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from image_differ import *


# Set the path where the test images reside
test_data_path = os.path.join(Path(os.path.abspath(os.path.dirname(__file__))), 'testdata')


@pytest.mark.parametrize('input_file1, input_file2, expected_perc',
                         [('original.png', '25perc.png', 25),
                          ('original.png', '50perc.png', 50),
                          ('original.png', '75perc.png', 75),
                          ('original.png', '100perc.png', 100),
                          ('complex1.png', 'complex2.png', 2),
                          ])
def test_image_perc(input_file1, input_file2, expected_perc):
    image_file1 = os.path.join(test_data_path, input_file1)
    image_file2 = os.path.join(test_data_path, input_file2)
    image_test = ImageDiffer()
    assert(round(image_test.image_diff(image_file1, image_file2)) == expected_perc)
