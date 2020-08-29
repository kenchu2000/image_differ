#########################################################################################
# A Python script that compares two images and get a delta % difference in image pixels.
# A good use case would be for testing an application to make sure the screen outputs
# are identical.
#
# by Ken Chu (kenchu2000@gmail.com)
#
#########################################################################################
from PIL import Image, ImageChops
from PIL import ImageFont
from PIL import ImageDraw
import os
from pathlib import Path
import base64
import traceback
import logging
import argparse
logger = logging.getLogger(__name__)


class ImageDiffer():
    def __init__(self):
        # Nothing to initialize for now
        pass

    def combine_images(self, *imgs, diff_percentage, output_image_file):
        images = list(map(Image.open, imgs))
        widths, heights = zip(*(i.size for i in images))
        # by default, the images will show side by side horizontally
        vertically = False
        font_file_path = os.path.join(Path(os.path.abspath(os.path.dirname(__file__))),
                                      'resources', 'arial.ttf')
        font = ImageFont.truetype(font_file_path, 14)

        # combining the first input_image, second input_image, and the delta output image into one single image
        if vertically:
            max_width = max(widths)
            total_height = sum(heights) + (len(imgs) * 100)
            new_im = Image.new('RGB', (max_width, total_height))

            y_offset = 0
            for idx, im in enumerate(images):
                new_im.paste(im, (0, y_offset))
                y_offset = y_offset + im.size[1] + 100
                draw = ImageDraw.Draw(new_im)
                if idx == len(imgs) - 1:
                    label = Path(imgs[idx]).name + ' (Diff = 0.2f%%)' % diff_percentage
                else:
                    label = Path(imgs[idx]).name

                draw.text((10, y_offset-80), label, (255, 255, 255), font=font)
        else:
            total_width = sum(widths) +  (len(imgs) * 100)
            max_height = max(heights) + 200
            new_im = Image.new('RGB', (total_width, max_height))

            x_offset = 0
            for idx, im in enumerate(images):
                new_im.paste(im, (x_offset, 80))
                orig_x_offset = x_offset + 10
                x_offset = x_offset + im.size[0] + 100
                draw = ImageDraw.Draw(new_im)
                if idx == len(imgs) - 1:
                    label = Path(imgs[idx]).name + ' (Diff = %0.2f%%)' % diff_percentage
                else:
                    label = Path(imgs[idx]).name
                draw.text((orig_x_offset, 10), label, (255, 255, 255), font=font)
        new_im.save(output_image_file)

    def image_diff(self, input_imgge1_file, input_image2_file, delta_image_file=None):
        # open the two images for comparison
        source_img = Image.open(input_imgge1_file)
        target_img = Image.open(input_image2_file)

        if source_img.size != target_img.size:
            logger.error('ERROR: The two images have different image size resolution.  Unable to perform image diff.')
            exit(2)

        # use the PIL library to get the difference between the two images
        diff = ImageChops.difference(source_img, target_img)

        # getbbox() is to calculate the bounding box of the non-black color regions in am image
        bbox = diff.getbbox()
        if bbox:
            if delta_image_file:
                # the default image mode is RGBA, and we will need to discard th A (A = alpha = transparency to be
                # able to save the pixel colors to a image file.
                discard_rgb_diff_image = diff.convert('RGB')
                discard_rgb_diff_image.save(delta_image_file)

            # obtain the width nd height of a diff image to calculate the total # of pixels
            width = diff.width
            height = diff.height
            total_diff_img_pixels = width * height

            # obtain the total number of non-black color pixels from a diff image
            total_diff_non_black_pixels = sum(diff.crop(bbox).point(lambda x: 255 if x else 0).convert("L").
                                              point(bool).getdata())

            logger.debug('Image Width: %d, Image Height: %d, Total Pixels: %d, Total Non-Black Pixels: %d' %
                  (width, height, total_diff_img_pixels, total_diff_non_black_pixels))

            # percentage difference, th higher the value, the bigger difference is between the to images
            return float(total_diff_non_black_pixels / total_diff_img_pixels) * 100
        else:
            # if getbbox() returns None, that means there is no non-black color pixels from an image, that means
            # the two images are completely identical.
            return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description='Python script that compares two images and return the delta pixel % difference.')
    parser.add_argument('--input_image1_file', required=True)
    parser.add_argument('--input_image2_file', required=True)
    parser.add_argument('--output_image_file', required=False)
    args = parser.parse_args()
    input_image1_file = args.input_image1_file
    input_image2_file = args.input_image2_file
    output_image_file = args.output_image_file
    if not os.path.isfile(input_image1_file):
        logger.error(f'FATAL: The input_image1_file {input_image1_file} does not exist!')
        exit(1)
    if not os.path.isfile(input_image2_file):
        logger.error(f'FATAL: The input_image2_file {input_image2_file} does not exist!')
        exit(1)

    image_differ = ImageDiffer()
    delta_image_file = os.path.join(Path(os.path.abspath(os.path.dirname(__file__))), 'tmp_delta_image.png')
    try:
        perc_diff = image_differ.image_diff(input_imgge1_file=input_image1_file,
                                            input_image2_file=input_image2_file,
                                            delta_image_file=delta_image_file)
        logger.info('Percentage difference between the two images: %.0f%%' % perc_diff)

        if output_image_file:
            image_differ.combine_images(input_image1_file, input_image2_file, delta_image_file,
                                         diff_percentage=perc_diff, output_image_file=output_image_file)
            if os.path.isfile(output_image_file):
                logger.info(f'The output file has been saved to {output_image_file}')
            else:
                logger.error(f'ERROR: Failed to save output file {output_image_file}')

    except FileNotFoundError as ex:
        logger.info(str(ex))
    except Exception as ex:
        logger.info(traceback.format_exc())
