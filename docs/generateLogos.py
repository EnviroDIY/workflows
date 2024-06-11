# %%
import os
import json
from PIL import ImageFont, Image, ImageDraw

# from IPython.display import display


# %%
# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys() and "DOC_ROOT" in os.environ.keys():
    docbuild_dir = os.environ.get("DOC_ROOT")
    repo_name = os.environ.get("GITHUB_REPOSITORY").split("/")[1]
else:
    docbuild_dir = os.getcwd()
    repo_name = docbuild_dir.replace("\\\\", "/").replace("\\", "/").split("/")[-1]

lib_specs_path = os.path.join(docbuild_dir, "library.json")
lib_specs_path = os.path.abspath(os.path.realpath(lib_specs_path))

print(f"Repository Name: {repo_name}")
print(f"Documentation Building Directory: {docbuild_dir}")
print("JSON Library Specs File: {}".format(lib_specs_path))

# %% parse the library info
with open(lib_specs_path) as f:
    lib_specs = json.load(f)
library_name = lib_specs["name"].replace("EnviroDIY_", "")
library_version = lib_specs["version"]

# %%
logo_sizes = {
    "gp-desktop-logo": {"width": 200, "height": 42},
    "gp-scrolling-logo": {"width": 264, "height": 55},
    "gp-mobile-logo": {"width": 132, "height": 28},
}
ubuntu_font = "Ubuntu-Bold.ttf"
# #8ec551 = rgb(142,197,81) = Greenish, library name
# #da9230 = rgb(218,146,48) = Orangeish, library version
# #222222 = rgb(34,34,34) = blackish header background
ediy_green = (142, 197, 81, 255)
ediy_orange = (218, 146, 48, 255)
# ediy_header_bkgd = (34, 34, 34)
ediy_header_bkgd = (255, 255, 255, 0)  # transparent


def get_font_size(text_1, text_2, max_width, max_height):
    font_size = 500
    fits_in_box = False
    while fits_in_box == False:
        font = ImageFont.truetype(font=ubuntu_font, size=font_size)
        # (left, top, right, bottom)
        left1, top1, right1, bottom1 = font.getbbox(text_1, mode="")
        rendered_width1 = right1 - left1
        rendered_height1 = bottom1 - top1
        left2, top2, right2, bottom2 = font.getbbox(text_2, mode="")
        rendered_width2 = right2 - left2
        rendered_height2 = bottom2 - top2
        if (
            rendered_width1 < max_width
            and rendered_width2 < max_width
            and rendered_height1 < max_height
            and rendered_height2 < max_height
        ):
            fits_in_box = True
        else:
            font_size -= 1
    return font_size


# %%
def create_logo(logo_type: str, library_name: str, library_version: str):
    logo_width = logo_sizes[logo_type]["width"]
    logo_height = logo_sizes[logo_type]["height"]
    center_x = int(logo_width / 2)
    center_y = int(logo_height / 2)
    # calculate the max font size
    font_size = get_font_size(library_name, library_version, logo_width, logo_height)
    # create a new image with a black background
    img = Image.new(mode="RGBA", size=(logo_width, logo_height), color=ediy_header_bkgd)
    # prepare to draw on the image
    draw = ImageDraw.Draw(img)
    # set the font for drawing text
    # font = ImageFont.truetype(<font-file>, <font-size>)
    font = ImageFont.truetype(font=ubuntu_font, size=font_size)
    # add the library name
    draw.text(
        xy=(center_x, center_y),  # set the baseline in the center
        text=library_name,
        fill=ediy_green,
        font=font,
        anchor="md",  # anchor x to the center an y to the descender
        # (bottom of the lowest letters)
    )
    # add the library version
    draw.text(
        xy=(center_x, center_y),  # set the baseline in the center
        text=library_version,
        fill=ediy_orange,
        font=font,
        anchor="ma",  # anchor x to the center an y to the ascender
        # (top of the tallest letters)
    )
    # display(img)
    img.save(f"docs/{logo_type}.png")


# %%
for logo_size in logo_sizes.keys():
    create_logo(logo_size, library_name, library_version)
