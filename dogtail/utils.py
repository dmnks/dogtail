# -*- coding: utf-8 -*-
"""
Various utilities

Authors: Ed Rousseau <rousseau@redhat.com>, Zack Cerza <zcerza@redhat.com, David Malcolm <dmalcolm@redhat.com>
"""

__author__ = """Ed Rousseau <rousseau@redhat.com>,
Zack Cerza <zcerza@redhat.com,
David Malcolm <dmalcolm@redhat.com>
"""

import os
import sys
import subprocess
import re
from config import config
from time import sleep
from logging import debugLogger as logger
from logging import TimeStamp
from errors import DependencyNotFoundError

def screenshot(file = 'screenshot.png', timeStamp = True):
    """
    This function wraps the ImageMagick import command to take a screenshot.

    The file argument may be specified as 'foo', 'foo.png', or using any other
    extension that ImageMagick supports. PNG is the default.

    By default, screenshot filenames are in the format of foo_YYYYMMDD-hhmmss.png .
    The timeStamp argument may be set to False to name the file foo.png.
    """
    if not isinstance(timeStamp, bool):
        raise TypeError, "timeStampt must be True or False"
    # config is supposed to create this for us. If it's not there, bail.
    assert os.path.isdir(config.scratchDir)

    baseName = ''.join(file.split('.')[0:-1])
    fileExt = file.split('.')[-1].lower()
    if not baseName:
        baseName = file
        fileExt = 'png'

    if timeStamp:
        ts = TimeStamp()
        newFile = ts.fileStamp(baseName) + '.' + fileExt
        path = config.scratchDir + newFile
    else:
        newFile = baseName + '.' + fileExt
        path = config.scratchDir + newFile

    import gtk.gdk
    import gobject
    rootWindow = gtk.gdk.get_default_root_window()
    geometry = rootWindow.get_geometry()
    pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, geometry[2], \
            geometry[3])
    gtk.gdk.Pixbuf.get_from_drawable(pixbuf, rootWindow, \
            rootWindow.get_colormap(), 0, 0, 0, 0, geometry[2], geometry[3])
    # gtk.gdk.Pixbuf.save() needs 'jpeg' and not 'jpg'
    if fileExt == 'jpg': fileExt = 'jpeg'
    try: pixbuf.save(path, fileExt)
    except gobject.GError:
        raise ValueError, "Failed to save screenshot in %s format" % fileExt
    assert os.path.exists(path)
    logger.log("Screenshot taken: " + path)
    return path

def run(string, timeout=config.runTimeout, interval=config.runInterval, desktop=None, dumb=False, appName=''):
    """
    Runs an application. [For simple command execution such as 'rm *', use os.popen() or os.system()]
    If dumb is omitted or is False, polls at interval seconds until the application is finished starting, or until timeout is reached.
    If dumb is True, returns when timeout is reached.
    """
    if not desktop: from tree import root as desktop
    args = string.split()
    name = args[0]
    os.environ['GTK_MODULES'] = 'gail:atk-bridge'
    pid = subprocess.Popen(args, env = os.environ).pid

    if not appName:
        appName=args[0]

    if dumb:
        # We're starting a non-AT-SPI-aware application. Disable startup detection.
        doDelay(timeout)
    else:
        # Startup detection code
        # The timing here is not totally precise, but it's good enough for now.
        time = 0
        while time < timeout:
            time = time + interval
            try:
                for child in desktop.children[::-1]:
                    if child.name == appName:
                        for grandchild in child.children:
                            if grandchild.roleName == 'frame':
                                from procedural import focus
                                focus.application.node = child
                                doDelay(interval)
                                return pid
            except AttributeError: pass
            doDelay(interval)
    return pid

def doDelay(delay=None):
    """
    Utility function to insert a delay (with logging and a configurable
    default delay)
    """
    if delay is None:
        delay = config.defaultDelay
    if config.debugSleep:
        logger.log("sleeping for %f" % delay)
    sleep(delay)

class Blinker:
    INTERVAL_MS = 200

    def __init__(self, x, y, w, h, count = 2):
        import gobject
        import gtk.gdk
        self.count = count
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.timeout_handler_id = gobject.timeout_add (Blinker.INTERVAL_MS, self.blinkDrawRectangle)
        gtk.main()

    def blinkDrawRectangle (self):
        import gtk.gdk
        display = gtk.gdk.display_get_default()
        screen = display.get_default_screen()
        rootWindow = screen.get_root_window()
        gc = rootWindow.new_gc()

        gc.set_subwindow (gtk.gdk.INCLUDE_INFERIORS)
        gc.set_function (gtk.gdk.INVERT)
        gc.set_line_attributes (3, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_BUTT, gtk.gdk.JOIN_MITER)
        rootWindow.draw_rectangle (gc, False, self.x, self.y, self.w, self.h);

        self.count-=1

        if self.count <= 0:
            gtk.main_quit()
            return False

        return True


a11yGConfKey = '/desktop/gnome/interface/accessibility'

def isA11yEnabled():
    """
    Checks if accessibility is enabled via gconf.
    """
    import gconf
    gconfEnabled = gconf.client_get_default().get_bool(a11yGConfKey)
    if os.environ.get('GTK_MODULES','').find('gail:atk-bridge') == -1:
        envEnabled = False
    else: envEnabled = True
    return (gconfEnabled or envEnabled)

def bailBecauseA11yIsDisabled():
    if sys.argv[0].endswith("pydoc"): return
    try:
        if file("/proc/%s/cmdline" % os.getpid()).read().find('epydoc') != -1:
            return
    except: pass
    logger.log("Dogtail requires that Assistive Technology support be enabled. Aborting...")
    sys.exit(1)

def enableA11y():
    """
    Enables accessibility via gconf.
    """
    import gconf
    return gconf.client_get_default().set_bool(a11yGConfKey, True)

def checkForA11y():
    """
    Checks if accessibility is enabled, and halts execution if it is not.
    """
    if not isA11yEnabled(): bailBecauseA11yIsDisabled()

def checkForA11yInteractively():
    """
    Checks if accessibility is enabled, and presents a dialog prompting the
    user if it should be enabled if it is not already, then halts execution.
    """
    if isA11yEnabled(): return
    import gtk
    dialog = gtk.Dialog('Enable Assistive Technology Support?',
                     None,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_QUIT, gtk.RESPONSE_CLOSE, 
                         "_Enable", gtk.RESPONSE_ACCEPT))
    question = """Dogtail requires that Assistive Technology Support be enabled for it to function. Would you like to enable Assistive Technology support now?

Note that you will have to log out for the change to fully take effect.
    """.strip()
    dialog.set_default_response(gtk.RESPONSE_ACCEPT)
    questionLabel = gtk.Label(question)
    questionLabel.set_line_wrap(True)
    dialog.vbox.pack_start(questionLabel)
    dialog.show_all()
    result = dialog.run()
    if result == gtk.RESPONSE_ACCEPT:
        logger.log("Enabling accessibility...")
        enableA11y()
    elif result == gtk.RESPONSE_CLOSE:
       bailBecauseA11yIsDisabled()
    dialog.destroy()

