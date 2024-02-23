from __future__ import annotations
from ._gt_data import GTData
from typing import Optional

import tempfile


def as_raw_html(self: GTData) -> str:
    """
    Get the HTML content of a GT object.

    Get the HTML content from a GT object as a string. This function is useful for obtaining the
    HTML content of a GT object for use in other contexts.

    Parameters
    ----------
    gt
        A GT object.

    Returns
    -------
    str
        An HTML fragment containing a table.
    """
    return self._build_data(context="html")._render_as_html()


def save(
    self: GTData,
    filename: str,
    path: Optional[str] = None,
    selector: str = "table",
    scale: float = 1.0,
    expand: int = 5,
    window_size: tuple[int, int] = (6000, 6000),
) -> None:
    """
    Save a table as an image file.

    The `save()` method makes it easy to save a table object as an image file. The function produces
    a high-resolution PNG file of the table. The image is created by taking a screenshot of
    the table using a headless Chrome browser. The screenshot is then cropped to only include the
    table element, and the resulting image is saved to the specified file path.

    Parameters
    ----------
    filename
        The name of the file to save the image to.
    path
        An optional path to save the image to. If not provided, the image will be saved to the
        current working directory.
    selector
        The HTML element selector to use to select the table. By default, this is set to "table",
        which selects the first table element in the HTML content.
    scale
        The scaling factor that will be used when generating the image. By default, this is set to a
        value of `1.0`. Lowering this will result in a smaller image, whereas increasing it will
        result in a much higher-resolution image. This can be considered a quality setting, yet it
        also affects the file size. The default value of `1.0` is a good balance between file size
        and quality.
    expand
        The number of pixels to expand the screenshot by. By default, this is set to 5. This can be
        increased to capture more of the surrounding area, or decreased to capture less.
    window_size
        The size of the window to use when taking the screenshot. This is a tuple of two integers,
        representing the width and height of the window. By default, this is set to `(6000, 6000)`,
        a large size that should be sufficient for most tables. If the table is larger than this
        (and this will be obvious once inspecting the image file) you can increase the appropriate
        values of the tuple. If the table is very small, then a reduction in these these values will
        result in a speed gain during image capture. Please note that the window size is *not* the
        same as the final image size. The table will be captured at the same size as it is displayed
        in the headless browser, and the window size is used to ensure that the entire table is
        visible in the screen capture before the cropping process occurs.

    Returns
    -------
    None
        This function does not return anything; it simply saves the image to the specified file
        path.

    Details
    -------
    We create the image file based on the HTML version of the table. With the filename extension
    .png, we get a PNG image file. This process is facilitated by two libraries:

    - `selenium`, which is used to control the Chrome browser and take a screenshot of the table.
    - `PIL`, which is used to crop the screenshot to only include the table element of the page.

    Both of these packages needs to be installed before attempting to save any table as an image
    file. The `selenium` package also requires the Chrome browser to be installed on the system.

    A pip-based reinstallation of **Great Tables** through the following command will install these
    required packages:

    ```bash
    pip install great_tables[extra]
    ```

    One of the arguments for PNG saving is `scale=`, which defaults to a scale value of `1.0`. This
    default provides adequate image quality for most use cases given that text and lines are
    rendered clearly. However, if you need a higher resolution, you can increase the `scale` level.
    Keep in mind that file sizes will increase quite a bit with higher scale levels. At the default
    scale level you should expect that `GT(exibble).save("exibble.png")` will produce a file of
    about 150 KB. At a scale level of `2.0`, the file size will be about 320 KB; on the flipside, a
    scale level of `0.5` yields a ~70 KB image.

    The `expand=` argument adds whitespace pixels around the cropped table image. This has a default
    value of `5`. This can be increased to capture more of the surrounding area, or decreased to
    capture less (to a natural limit of `0`). The table is always captured on a white background, so
    the `expand=` value can be useful to add some padding around the table in the image file.
    """

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from PIL import Image
    from io import BytesIO
    from pathlib import Path

    Image.MAX_IMAGE_PIXELS = None

    # Get the HTML content from the displayed output
    html_content = as_raw_html(self=self)

    # Create a temp directory to store the HTML file
    temp_dir = tempfile.mkdtemp()

    # Create a temp file to store the HTML file; use the .html file extension
    temp_file = tempfile.mkstemp(dir=temp_dir, suffix=".html")

    # Write the HTML content to the temp file
    with open(temp_file[1], "w") as f:
        f.write(html_content)

    # Generate output file path from filename and optional path
    output_path = filename
    if path:
        # If path has a trailing slash, remove it; use the Path class to handle this
        path = Path(path)
        if path.is_dir():
            output_path = path / filename
        else:
            path = path.parent
            output_path = path / filename
    else:
        output_path = Path.cwd() / filename

    # Set up the Chrome webdriver options
    options = webdriver.ChromeOptions()

    # Use headless mode with an extremely large window size
    options.add_argument("--headless")

    # Set the window size (x by y) to a large value to ensure the entire table
    # is visible in the screenshot; this is settable via the `window_size=` argument
    options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")

    # Instantiate a Chrome webdriver with the selected options
    chrome = webdriver.Chrome(options=options)

    # Convert the scale value to a percentage string used by the
    # Chrome browser for zooming
    zoom_level = str(scale * 100) + "%"

    # Get the scaling factor by multiplying `scale` by 2
    scaling_factor = scale * 2

    # Adjust the expand value by the scaling factor
    expansion_amount = expand * scaling_factor

    # Open the HTML file in the Chrome browser
    chrome.get("file://" + temp_file[1])
    chrome.execute_script(f"document.body.style.zoom = '{zoom_level}'")

    # Get only the chosen element from the page; by default, this is
    # the table element
    element = chrome.find_element(by=By.TAG_NAME, value=selector)

    # Get the location and size of the table element; this will be used
    # to crop the screenshot later
    location = element.location
    size = element.size

    # Get a screenshot of the entire page
    png = chrome.get_screenshot_as_png()

    # Close the Chrome browser
    chrome.quit()

    # Open the screenshot as an image with the PIL library; since the screenshot will be large
    # (due to the large window size), we use the BytesIO class to handle the large image data
    image = Image.open(fp=BytesIO(png))

    # Crop the image to only include the table element; the scaling factor
    # of 6 is used to account for the zoom level of 300% set earlier
    left = (location["x"] * scaling_factor) - expansion_amount
    top = (location["y"] * scaling_factor) - expansion_amount
    right = ((location["x"] + size["width"]) * scaling_factor) + expansion_amount
    bottom = ((location["y"] + size["height"]) * scaling_factor) + expansion_amount

    # Save the cropped image to the output path
    image = image.crop((left, top, right, bottom))

    # Save the image to the output path as a PNG file
    image.save(fp=output_path, format="png")
