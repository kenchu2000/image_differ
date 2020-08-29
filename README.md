# About image_differ.py

image_differ.py is a Python script that takes two images and compare the delta percentage difference and also return the output of the delta image.  One good use case is to compare the image generation functions ensure thier consistency.

# Instructions

Running this script is quite simple.  You can run the script using the following steps:

1. Install Python 3.8.x and Git if not already installed.
2. Create virtual environment (optional but highly recomended)
  - git clone https@github.com:kenchu2000/image_differ.git
  - cd image_differ
  - pip3 install virtualenv
  - virtualenv -p python3 venv
  - source ./venv/bin/activate
3. pip3 install -r requirements.txt
4. Run python3 --input_image1_file <image_file> --input_image2_file <image_file> --output_image_file <image_file>

**Example:** *python3 --input_image1_file ./image1.png --input_image2_file ./image2.png --output_image_file ./delta_output.png*

Below is the sample detla_output.png:

![delta_output.png](/docs/images/delta_output.png)
