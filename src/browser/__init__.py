"""
Browser control and automation module.
"""

from src.browser.controller import BrowserController, BrowserAction
from src.browser.dom_helper import clean_html

__all__ = ["BrowserController", "BrowserAction", "clean_html"]
