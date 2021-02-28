import atexit
import os
import pdb
import sys
import time
from pathlib import Path
from typing import List, Optional

import psutil
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

ROAM_FORMATS = ("json", "markdown", "edn")


class Browser:
    FIREFOX = "Firefox"
    PHANTOMJS = "PhantomJS"
    CHROME = "Chrome"

    def __init__(self, browser, output_directory, headless=True, debug=False):
        if browser == Browser.FIREFOX:
            logger.trace("Configure Firefox Profile Firefox")
            firefox_profile = webdriver.FirefoxProfile()

            firefox_profile.set_preference("browser.download.folderList", 2)
            firefox_profile.set_preference("browser.download.manager.showWhenStarting", False)
            firefox_profile.set_preference("browser.download.dir", str(output_directory))
            firefox_profile.set_preference(
                "browser.helperApps.neverAsk.saveToDisk", "application/zip")

            logger.trace("Configure Firefox Profile Options")
            firefox_options = webdriver.FirefoxOptions()
            if headless:
                logger.trace("Set Firefox as headless")
                firefox_options.headless = True

            logger.trace("Start Firefox")
            self.browser = webdriver.Firefox(firefox_profile=firefox_profile,
                                             firefox_options=firefox_options)
        elif browser == Browser.PHANTOMJS:
            raise NotImplementedError()
            # TODO configure
            # self.browser = webdriver.PhantomJS()
        elif browser == Browser.Chrome:
            raise NotImplementedError()
            # TODO configure
            # self.browser = webdriver.Chrome()
        else:
            raise ValueError(f"Invalid browser '{browser}")

        self.debug = debug

    def get(self, url):
        if self.debug:
            try:
                self.browser.get(url)
            except Exception:
                pdb.set_trace()
        else:
            self.browser.get(url)

    def find_element_by_css_selector(self, css_selector, check=True) -> "HTMLElement":
        if self.debug and check:
            try:
                return self.browser.find_element_by_css_selector(css_selector)
            except NoSuchElementException:
                pdb.set_trace()
                raise
        element = self.browser.find_element_by_css_selector(css_selector)
        return HTMLElement(element, debug=self.debug)

    def find_element_by_link_text(self, text) -> "HTMLElement":
        elements = self.browser.find_elements_by_link_text(text)
        if len(elements) != 1:
            if self.debug:
                pdb.set_trace()
            elements_str = [e.text for e in elements]
            raise ValueError(
                f"Got {len(elements)} elements, expected 1 for {text}: {elements_str}")
        element, = elements
        return HTMLElement(element, debug=self.debug)

    def close(self):
        self.browser.close()


class HTMLElement:
    def __init__(self, html_element: webdriver.remote.webelement.WebElement, debug=False):
        self.html_element = html_element
        self.debug = debug

    def click(self):
        if self.debug:
            try:
                return self.html_element.click()
            except Exception:
                pdb.set_trace()
        else:
            return self.html_element.click()

    def send_keys(self, keys: str):
        if self.debug:
            try:
                return self.html_element.send_keys(keys)
            except Exception:
                pdb.set_trace()
        else:
            return self.html_element.send_keys(keys)

    @property
    def text(self) -> str:
        return self.html_element.text


class Config:
    def __init__(self,
                 browser: str,
                 database: Optional[str],
                 debug: bool,
                 gui: bool,
                 sleep_duration: float = 2.,
                 browser_args: Optional[List[str]] = None):
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
        self.gui = gui
        self.sleep_duration = sleep_duration
        self.browser = getattr(Browser, browser.upper())
        self.browser_args = (browser_args or [])


def download_rr_archive(output_type: str,
                        output_directory: Path,
                        config: Config,
                        slow_motion=10,
                        ):
    logger.debug("Creating browser")
    browser = Browser(browser=config.browser,
                      headless=not config.gui,
                      debug=config.debug,
                      output_directory=output_directory)

    if config.debug:
        pass
    try:
        return _download_rr_archive(browser, output_type, output_directory, config)
    except (KeyboardInterrupt, SystemExit):
        logger.debug("Closing browser on interrupt {}", output_type)
        browser.close()
        logger.debug("Closed browser {}", output_type)
        raise
    finally:
        logger.debug("Closing browser {}", output_type)
        browser.close()
        logger.debug("Closed browser {}", output_type)


def _download_rr_archive(browser: Browser,
                         output_type: str,
                         output_directory: Path,
                         config: Config,
                         ):
    """Download an archive in RoamResearch.

    :param output_type: Download JSON or Markdown or EDN
    :param output_directory: Directory where to stock the outputs
    """
    signin(browser, config, sleep_duration=config.sleep_duration)

    if config.database:
        go_to_database(browser, config.database)

    logger.debug("Wait for interface to load")
    dot_button = None
    for _ in range(100):
        # Starting is a little bit slow, so we wait for the button that signal it's ok
        time.sleep(config.sleep_duration)
        try:
            dot_button = browser.find_element_by_css_selector(".bp3-icon-more", check=False)
            break
        except NoSuchElementException:
            pass

        # If we have multiple databases, we will be stuck. Let's detect that.
        time.sleep(config.sleep_duration)
        try:
            strong = browser.find_element_by_css_selector("strong", check=False)
        except NoSuchElementException:
            continue
        if "database's you are an admin of" == strong.text.lower():
            logger.error(
                "You seems to have multiple databases. Please select it with the option "
                "--database")
            sys.exit(1)

    assert dot_button is not None, "All roads leads to Roam, but that one is too long. Try " \
                                   "again when Roam servers are faster."

    # Click on something empty to remove the eventual popup
    # "Sync Quick Capture Notes with Workspace"
    # TODO browser.mouse.click(0, 0)

    dot_button.click()

    logger.debug("Launch download popup")
    export_all = browser.find_element_by_link_text("Export All")
    export_all.click()
    time.sleep(config.sleep_duration)

    # Configure download type
    dropdown_button = browser.find_element_by_css_selector(".bp3-dialog .bp3-button-text")
    if output_type.lower() != dropdown_button.text.lower():
        logger.debug("Changing output type to {}", output_type)
        dropdown_button.click()
        output_type_elem = browser.find_element_by_link_text(output_type.upper())
        output_type_elem.click()

    # defensive check
    assert dropdown_button.text.lower() == output_type.lower(), (dropdown_button.text, output_type)

    # Click on "Export All"
    export_all_confirm = browser.find_element_by_css_selector(".bp3-intent-primary")
    export_all_confirm.click()

    logger.debug("Wait download of {} to {}", output_type, output_directory)
    for i in range(1, 60 * 10):
        time.sleep(1)
        if i % 60 == 0:
            logger.debug("Keep waiting for {}, {}s elapsed", output_type, i)
        for file in output_directory.iterdir():
            if file.name.endswith(".zip"):
                logger.debug("File {} found for {}", file, output_type)
                time.sleep(1)
                return
    logger.debug("Waiting too long {}")
    raise FileNotFoundError("Impossible to download {} in {}", output_type, output_directory)


def signin(browser, config: Config, sleep_duration=1.):
    """Sign-in into Roam"""
    logger.debug("Opening signin page")
    browser.get('https://roamresearch.com/#/signin')
    # increased to 5 seconds to handle sporadic second login screen refresh
    time.sleep(6.)

    logger.debug("Fill email '{}'", config.user)
    email_elem = browser.find_element_by_css_selector("input[name='email']")
    email_elem.send_keys(config.user)

    logger.debug("Fill password")
    passwd_elem = browser.find_element_by_css_selector("input[name='password']")
    passwd_elem.send_keys(config.password)
    passwd_elem.send_keys(Keys.RETURN)


def go_to_database(browser, database):
    """Go to the database page"""
    url = f'https://roamresearch.com/#/app/{database}'
    logger.debug(f"Load database from url '{url}'")
    browser.get(url)


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


def scrap(zip_path: Path, formats: List[str], config: Config):
    # Register to always kill child process when the script close, to not have zombie process.
    # TODO: is is still needed with Selenium?
    if not config.debug:
        atexit.register(_kill_child_process)

    for f in formats:
        format_zip_path = zip_path / f
        format_zip_path.mkdir(exist_ok=True)
        download_rr_archive(f, format_zip_path, config=config)
