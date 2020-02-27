#!/usr/bin/env python3
# coding: utf-8

import argparse
import asyncio
import os
from pathlib import Path

from pyppeteer import launch


def patch_pyppeteer():
    """Fix https://github.com/miyakogi/pyppeteer/issues/178"""
    import pyppeteer.connection
    original_method = pyppeteer.connection.websockets.client.connect

    def new_method(*args, **kwargs):
        kwargs['ping_interval'] = None
        kwargs['ping_timeout'] = None
        return original_method(*args, **kwargs)

    pyppeteer.connection.websockets.client.connect = new_method


patch_pyppeteer()


async def get_text(page, b, norm=True):
    """Get the inner text of an element"""
    text = await page.evaluate('(element) => element.textContent', b)
    if norm:
        text = text.lower().strip()
    return text


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_type", help="Download JSON or Markdown")
    parser.add_argument("--devtools", action="store_true",
                        help="Should we open Chrome")
    parser.add_argument("--sleep_duration", type=float, default=0.1,
                        help="How many seconds to wait after the clicks")
    parser.add_argument("--download_duration", type=float, default=10,
                        help="How many seconds to before to close the browser when the "
                             "download is started")
    parser.add_argument("--slow_motion", type=float, default=10,
                        help="Slow motion in Pyppeter")
    parser.add_argument("--output_directory", default=str(Path.home() / "Downloads"),
                        help="Directory where to stock the outputs")
    args = parser.parse_args()

    output_type = args.output_type
    sleep_duration = args.sleep_duration
    download_duration = args.download_duration
    slow_motion = args.slow_motion
    devtools = args.devtools
    output_directory = args.output_directory

    print("Creating browser")
    browser = await launch(devtools=devtools, slowMo=slow_motion)
    document = await browser.newPage()

    if not devtools:
        print("Configure downloads to", output_directory)
        cdp = await document.target.createCDPSession()
        await cdp.send('Page.setDownloadBehavior',
                       {'behavior': 'allow', 'downloadPath': output_directory})

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
    await dot_button.click()

    print("Launch popup")
    divs_pb3 = await document.querySelectorAll(".bp3-fill")
    export_all, = [b for b in divs_pb3 if await get_text(document, b) == 'export all']
    await export_all.click()
    await asyncio.sleep(sleep_duration)

    async def get_dropdown_button():
        button = await document.querySelector(".bp3-button-text")
        button_text = await get_text(document, button)
        assert button_text in ["markdown",
                               "json"], button_text  # defensive check
        return button, button_text

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

    print("Waiting for the download to finish")
    await asyncio.sleep(download_duration)

    print("Closing the browser")
    await browser.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
