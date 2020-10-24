import asyncio
import atexit
import os
import sys
from pathlib import Path
from typing import Optional

import psutil
import pyppeteer.connection
from loguru import logger
from pyppeteer.page import Page


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
    def __init__(self, database: Optional[str], debug: bool, sleep_duration: float = 2.):
        self.user = os.environ["ROAMRESEARCH_USER"]
        self.password = os.environ["ROAMRESEARCH_PASSWORD"]
        assert self.user
        assert self.password
        if database:
            self.database: Optional[str] = database
        else:
            self.database = os.environ["ROAMRESEARCH_DATABASE"]
        assert self.database, "Please define the Roam database you want to backup."
        self.debug = debug
        self.sleep_duration = sleep_duration


async def download_rr_archive(output_type: str,
                              output_directory: Path,
                              config: Config,
                              slow_motion=10,
                              ):
    logger.debug("Creating browser")
    browser = await pyppeteer.launch(devtools=config.debug,
                                     slowMo=slow_motion,
                                     autoClose=False,
                                     )
    if config.debug:
        # We want the browser to stay open for debugging the interface
        pages = await browser.pages()
        document = pages[0]
        return await _download_rr_archive(document, output_type, output_directory, config)

    try:
        pages = await browser.pages()
        document = pages[0]
        return await _download_rr_archive(document, output_type, output_directory, config)
    except (KeyboardInterrupt, SystemExit):
        logger.debug("Closing browser on interrupt {}", output_type)
        await browser.close()
        logger.debug("Closed browser {}", output_type)
        raise
    finally:
        logger.debug("Closing browser {}", output_type)
        await browser.close()
        logger.debug("Closed browser {}", output_type)


async def _download_rr_archive(document: Page,
                               output_type: str,
                               output_directory: Path,
                               config: Config,
                               ):
    """Download an archive in RoamResearch.

    :param output_type: Download JSON or Markdown
    :param output_directory: Directory where to stock the outputs
    """
    if not config.debug:
        logger.debug("Configure downloads to {}", output_directory)
        cdp = await document.target.createCDPSession()
        await cdp.send('Page.setDownloadBehavior',
                       {'behavior': 'allow', 'downloadPath': str(output_directory)})

    await signin(document, config, sleep_duration=config.sleep_duration)

    if config.database:
        await go_to_database(document, config.database)

    logger.debug("Wait for interface to load")
    dot_button = None
    for _ in range(100):
        # Starting is a little bit slow, so we wait for the button that signal it's ok
        await asyncio.sleep(config.sleep_duration)
        dot_button = await document.querySelector(".bp3-icon-more")
        if dot_button is not None:
            break

        # If we have multiple databases, we will be stuck. Let's detect that.
        await asyncio.sleep(config.sleep_duration)
        strong = await document.querySelector("strong")
        if strong:
            if "database's you are an admin of" == await get_text(document, strong):
                logger.error(
                    "You seems to have multiple databases. Please select it with the option "
                    "--database")
                sys.exit(1)

    assert dot_button is not None, "All roads leads to Roam, but that one is too long. Try " \
                                   "again when Roam servers are faster."

    # Click on something empty to remove the eventual popup
    # "Sync Quick Capture Notes with Workspace"
    await document.mouse.click(0, 0)

    await dot_button.click()

    logger.debug("Launch download popup")
    divs_pb3 = await document.querySelectorAll(".bp3-fill")
    export_all, = [b for b in divs_pb3 if await get_text(document, b) == 'export all']
    await export_all.click()
    await asyncio.sleep(config.sleep_duration)

    async def get_dropdown_button():
        dropdown_button = await document.querySelector(".bp3-dialog .bp3-button-text")
        assert dropdown_button is not None
        dropdown_button_text = await get_text(document, dropdown_button)
        # Defensive check if the interface change
        assert dropdown_button_text in ["markdown", "json"], dropdown_button_text
        return dropdown_button, dropdown_button_text

    logger.debug("Checking download type")
    button, button_text = await get_dropdown_button()

    if button_text != output_type:
        logger.debug("Changing output type to {}", output_type)
        await button.click()
        await asyncio.sleep(config.sleep_duration)
        output_type_elems = await document.querySelectorAll(".bp3-text-overflow-ellipsis")
        output_type_elem, = [e for e in output_type_elems if await get_text(document, e) == output_type]
        await output_type_elem.click()

        # defensive check
        await asyncio.sleep(config.sleep_duration)
        _, button_text_ = await get_dropdown_button()
        assert button_text_ == output_type, (button_text_, output_type)

    logger.debug("Downloading output of type {}", output_type)
    buttons = await document.querySelectorAll('button')
    export_all_confirm, = [b for b in buttons if await get_text(document, b) == 'export all']
    await export_all_confirm.click()

    logger.debug("Wait download of {} to {}", output_type, output_directory)
    if config.debug:
        # No way to check because download location is not specified
        return
    for i in range(1, 60 * 10):
        await asyncio.sleep(1)
        if i % 60 == 0:
            logger.debug("Keep waiting for {}, {}s elapsed", output_type, i)
        for file in output_directory.iterdir():
            if file.name.endswith(".zip"):
                logger.debug("File {} found for {}", file, output_type)
                await asyncio.sleep(1)
                return
    logger.debug("Waiting too long {}")
    raise FileNotFoundError("Impossible to download {} in {}", output_type, output_directory)


async def signin(document, config: Config, sleep_duration=1.):
    """Sign-in into Roam"""
    logger.debug("Opening signin page")
    await document.goto('https://roamresearch.com/#/signin')
    await asyncio.sleep(sleep_duration)

    logger.debug("Fill email '{}'", config.user)
    email_elem = await document.querySelector("input[name='email']")
    await email_elem.click()
    await email_elem.type(config.user)

    logger.debug("Fill password")
    passwd_elem = await document.querySelector("input[name='password']")
    await passwd_elem.click()
    await passwd_elem.type(config.password)

    logger.debug("Click on sign-in")
    buttons = await document.querySelectorAll('button')
    signin_confirm, = [b for b in buttons if await get_text(document, b) == 'sign in']
    await signin_confirm.click()
    await asyncio.sleep(sleep_duration)


async def go_to_database(document, database):
    """Go to the database page"""
    url = f'https://roamresearch.com/#/app/{database}'
    logger.debug(f"Load database from url '{url}'")
    await document.goto(url)


def _kill_child_process(timeout=50):
    procs = psutil.Process().children(recursive=True)
    if not procs:
        return
    logger.debug("Terminate child process {}", procs)
    for p in procs:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    gone, still_alive = psutil.wait_procs(procs, timeout=timeout)
    if still_alive:
        logger.warning(f"Kill child process {still_alive} that was still alive after "
                       f"'timeout={timeout}' from 'terminate()' command")
        for p in still_alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass


def scrap(markdown_zip_path: Path, json_zip_path: Path, config: Config):
    # Just for easier run from the CLI
    markdown_zip_path = Path(markdown_zip_path)
    json_zip_path = Path(json_zip_path)

    tasks = [download_rr_archive("markdown", Path(markdown_zip_path), config=config),
             download_rr_archive("json", Path(json_zip_path), config=config),
             ]
    # Register to always kill child process when the script close, to not have zombie process.
    # Because of https://github.com/miyakogi/pyppeteer/issues/274 without this patch it does happen
    # a lot.
    if not config.debug:
        atexit.register(_kill_child_process)
    if config.debug:
        for task in tasks:
            # Run sequentially for easier debugging
            asyncio.get_event_loop().run_until_complete(task)
        logger.warning("Exiting without updating the git repository, "
                       "because we can't get the downloads with the option --debug")
    else:
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.debug("Scrapping finished")
