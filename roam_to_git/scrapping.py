import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

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


class Config:
    def __init__(self, database: Optional[str], debug: bool):
        self.user = os.environ["ROAMRESEARCH_USER"]
        self.password = os.environ["ROAMRESEARCH_PASSWORD"]
        assert self.user
        assert self.password
        if database:
            self.database = database
        else:
            self.database = os.environ.get("ROAMRESEARCH_DATABASE")
        self.debug = debug


async def download_rr_archive(output_type: str,
                              output_directory: Path,
                              config: Config,
                              sleep_duration=1.,
                              slow_motion=10,
                              ):
    """Download an archive in RoamResearch.

    :param output_type: Download JSON or Markdown
    :param output_directory: Directory where to stock the outputs
    :param devtools: Should we open Chrome
    :param sleep_duration: How many seconds to wait after the clicks
    :param slow_motion: How many seconds to before to close the browser when the download is started
    """
    print("Creating browser")
    browser = await pyppeteer.launch(devtools=config.debug, slowMo=slow_motion)
    document = await browser.newPage()

    if not config.debug:
        print("Configure downloads to", output_directory)
        cdp = await document.target.createCDPSession()
        await cdp.send('Page.setDownloadBehavior',
                       {'behavior': 'allow', 'downloadPath': str(output_directory)})

    await signin(document, config, sleep_duration=sleep_duration)

    if config.database:
        await go_to_database(document, config.database)

    print("Wait for interface to load")
    dot_button = None
    for _ in range(100):
        # Starting is a little bit slow, so we wait for the button that signal it's ok
        dot_button = await document.querySelector(".bp3-icon-more")
        if dot_button is not None:
            break

        # If we have multiple databases, we will be stuck. Let's detect that.
        strong = await document.querySelector("strong")
        if strong:
            if "database's you are an admin of" == await get_text(document, strong):
                print("You seems to have multiple databases. Please select it with the option "
                      "--database")
                sys.exit(1)

        await asyncio.sleep(sleep_duration)
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

    print("Wait download of", output_type, "to", output_directory)
    if config.debug:
        # No way to check because download location is not specified
        return
    for i in range(1, 1_001):
        await asyncio.sleep(0.1)
        if i % 10 == 0:
            sys.stdout.write("\n" if i % 600 == 0 else "x" if i % 100 == 0 else ".")
            sys.stdout.flush()
        for file in output_directory.iterdir():
            if file.name.endswith(".zip"):
                print("File", file, "found")
                await asyncio.sleep(1)
                await browser.close()
                return
    await browser.close()
    raise FileNotFoundError(f"Impossible to download {output_type} in {output_directory}")


async def signin(document, config: Config, sleep_duration=1.):
    """Sign-in into Roam"""
    print("Opening signin page")
    await document.goto('https://roamresearch.com/#/signin')
    await asyncio.sleep(sleep_duration)

    print(f"Fill email '{config.user}'")
    email_elem = await document.querySelector("input[name='email']")
    await email_elem.click()
    await email_elem.type(config.user)

    print("Fill password")
    passwd_elem = await document.querySelector("input[name='password']")
    await passwd_elem.click()
    await passwd_elem.type(config.password)

    print("Click on sign-in")
    buttons = await document.querySelectorAll('button')
    signin_confirm, = [b for b in buttons if await get_text(document, b) == 'sign in']
    await signin_confirm.click()
    await asyncio.sleep(sleep_duration)


async def go_to_database(document, database):
    """Go to the database page"""
    url = f'https://roamresearch.com/#/app/{database}'
    print(f"Load database from url '{url}'")
    await document.goto(url)


def scrap(markdown_zip_path: Path, json_zip_path: Path, config: Config):
    # Just for easier run from the CLI
    markdown_zip_path = Path(markdown_zip_path)
    json_zip_path = Path(json_zip_path)

    tasks = [download_rr_archive("markdown", Path(markdown_zip_path), config=config),
             download_rr_archive("json", Path(json_zip_path), config=config),
             ]
    if config.debug:
        for task in tasks:
            # Run sequentially for easier debugging
            asyncio.get_event_loop().run_until_complete(task)
        print("Exiting without updating the git repository, "
              "because we can't get the downloads with the option --debug")
        return
    else:
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
