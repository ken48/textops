from __future__ import annotations

import logging
from typing import Any

import objc
from Cocoa import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSStatusBar,
    NSWorkspace,
)

from .paths import LOG_FILE, resource_path

_HANDLER: Handler | None = None


class Handler(NSObject):
    worker: Any
    status_item: Any
    menu: Any

    def initWithWorker_(self, worker: Any) -> Handler | None:
        self = objc.super(Handler, self).init()
        if self is None:
            return None
        self.worker = worker
        self.status_item = None
        self.menu = None
        return self

    def buildMenu(self) -> None:
        # Create status bar item + menu
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1.0)

        # Try to set a real template image from Resources
        icon_path = resource_path("warmpyStatusTemplate.png")

        if icon_path.exists():
            img = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
            if img is not None:
                img.setTemplate_(True)

                btn = None
                try:
                    btn = self.status_item.button()
                except Exception:
                    btn = None

                if btn is not None:
                    btn.setTitle_("")
                    btn.setImage_(img)
                else:
                    # Older API fallback
                    self.status_item.setTitle_("")
                    try:
                        self.status_item.setImage_(img)
                    except Exception:
                        # If even that fails, fall back to a simple title.
                        self.status_item.setTitle_("W")
                        logging.warning("STATUS icon_set failed; fallback title=W")
        else:
            # Fallback if resource not found
            self.status_item.setTitle_("W")

        # Menu
        self.menu = NSMenu.alloc().init()

        open_log = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open Log", "openLog:", ""
        )
        open_log.setTarget_(self)
        self.menu.addItem_(open_log)

        self.menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quit:", ""
        )
        quit_item.setTarget_(self)
        self.menu.addItem_(quit_item)

        self.status_item.setMenu_(self.menu)

    def dispatchJob_(self, job: Any) -> None:
        self.worker._run_job(job)

    @objc.python_method
    def dispatchToMainThread(self, job: Any) -> None:
        self.performSelectorOnMainThread_withObject_waitUntilDone_("dispatchJob:", job, False)

    def openLog_(self, _sender: Any) -> None:
        try:
            NSWorkspace.sharedWorkspace().openFile_(str(LOG_FILE))
        except Exception:
            logging.exception("Open log failed")

    def quit_(self, _sender: Any) -> None:
        NSApplication.sharedApplication().terminate_(None)


def run_app(worker: Any, server: Any) -> None:
    global _HANDLER

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    _HANDLER = Handler.alloc().initWithWorker_(worker)
    if _HANDLER is None:
        logging.error("UI handler init failed")
        return

    worker.attach_main_thread_dispatcher(_HANDLER.dispatchToMainThread)
    _HANDLER.buildMenu()
    if not server.start():
        return

    logging.info("UI started")
    app.run()
