import asyncio
import os
from pathlib import Path

import pyppeteer.connection


def patch_pyppeteer():
    """Fix https://github.com/miyakogi/pyppeteer/issues/178"""
    import pyppeteer.connection
    original_method = pyppeteer.connection.websockets.client.connect

    def new_method(*args, **kwargs):
        kwargs['ping_interval'] = None
        kwargs['ping_timeout'] = None
        return original_method(*args, **kwargs)

    pyppeteer.connection.websockets.client.connect = new_method


async def get_text(page, b, norm=True):
    """Get the inner text of an element"""
    text = await page.evaluate('(element) => element.textContent', b)
    if norm:
        text = text.lower().strip()
    return text


async def download_rr_archive(output_type: str,
                              output_directory: Path,
                              devtools=False,
                              sleep_duration=1.,
                              slow_motion=10):
    """Download an archive in RoamResearch.

    :param output_type: Download JSON or Markdown
    :param output_directory: Directory where to stock the outputs
    :param devtools: Should we open Chrome
    :param sleep_duration: How many seconds to wait after the clicks
    :param slow_motion: How many seconds to before to close the browser when the download is started
    """
    print("Creating browser")
    browser = await pyppeteer.launch(devtools=devtools, slowMo=slow_motion)
    document = await browser.newPage()

    if not devtools:
        print("Configure downloads to", output_directory)
        cdp = await document.target.createCDPSession()
        await cdp.send('Page.setDownloadBehavior',
                       {'behavior': 'allow', 'downloadPath': str(output_directory)})

    print("Opening signin page")
    await document.goto('https://roamresearch.com/#/signin')
    await asyncio.sleep(sleep_duration)

    print("Fill email")
    email_elem = await document.querySelector("input[name='email']")
    await email_elem.click()
    await email_elem.type(os.environ["ROAMRESEARCH_USER"])

    print("Fill password")
    passwd_elem = await document.querySelector("input[name='password']")
    await passwd_elem.click()
    await passwd_elem.type(os.environ["ROAMRESEARCH_PASSWORD"])

    print("Click on sign-in")
    buttons = await document.querySelectorAll('button')
    signin_confirm, = [b for b in buttons if await get_text(document, b) == 'sign in']
    await signin_confirm.click()
    await asyncio.sleep(sleep_duration)

    print("Wait for interface to load")
    dot_button = None
    for _ in range(100):
        # Starting is a little bit slow
        dot_button = await document.querySelector(".bp3-icon-more")
        if dot_button is None:
            await asyncio.sleep(sleep_duration)
        else:
            break
    assert dot_button is not None
    await dot_button.click()

    print("Launch popup")
    divs_pb3 = await document.querySelectorAll(".bp3-fill")
    export_all, = [b for b in divs_pb3 if await get_text(document, b) == 'export all']
    await export_all.click()
    await asyncio.sleep(sleep_duration)

    async def get_dropdown_button():
        dropdown_button = await document.querySelector(".bp3-button-text")
        dropdown_button_text = await get_text(document, dropdown_button)
        # Defensive check if the interface change
        assert dropdown_button_text in ["markdown", "json"], dropdown_button_text
        return dropdown_button, dropdown_button_text

    print("Checking download type")
    button, button_text = await get_dropdown_button()

    if button_text != output_type:
        print("Changing output type to", output_type)
        await button.click()
        await asyncio.sleep(sleep_duration)
        output_type_elem, = await document.querySelectorAll(".bp3-text-overflow-ellipsis")
        await output_type_elem.click()

        # defensive check
        await asyncio.sleep(sleep_duration)
        _, button_text_ = await get_dropdown_button()
        assert button_text_ == output_type, (button_text_, output_type)

    print("Downloading output of type", output_type)
    buttons = await document.querySelectorAll('button')
    export_all_confirm, = [b for b in buttons if await get_text(document, b) == 'export all']
    await export_all_confirm.click()

    # Wait for download to finish
    if devtools:
        # No way to check because download location is not specified
        return
    for _ in range(1000):
        await asyncio.sleep(0.1)
        for file in output_directory.iterdir():
            if file.name.endswith(".zip"):
                print("File", file, "found")
                await asyncio.sleep(1)
                await browser.close()
                return
    await browser.close()
    raise FileNotFoundError(f"Impossible to download {output_type} in {output_directory}")
