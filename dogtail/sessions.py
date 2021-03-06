import time
import os
import errno
import re
import subprocess
import signal
import tempfile
import random
import glob
from dogtail.config import config

def scratchFile(label):
    """Uses tempfile.NamedTemporaryFile() to create a unique tempfile in 
    config.scratchDir, with a filename like: 
    dogtail-headless-<label>.<random junk>"""
    prefix = "dogtail-headless-"
    return tempfile.NamedTemporaryFile(prefix = "%s%s." % (prefix, label), 
            dir = config.scratchDir)

def testBinary(path):
    if (path.startswith(os.path.sep) or
            path.startswith(os.path.join('.','')) or 
            path.startswith(os.path.join('..',''))):
        if not os.path.exists(path):
            raise IOError, (errno.ENOENT, "No such file", path)
        if not os.access(path, os.X_OK):
            raise IOError, (errno.ENOEXEC, "Permission denied", path)
    return True

class Subprocess(object):
    def __init__(self, cmdList, environ=None, stdout=None, stderr=None):
        testBinary(cmdList[0])
        self.cmdList = cmdList
        self.environ = environ
        self.stdout = stdout
        self.stderr = stderr
        self._exitCode = None

    def start(self):
        if self.environ == None: environ = os.environ
        self.popen = subprocess.Popen(self.cmdList, env=self.environ,
                                      stdout=self.stdout, stderr=self.stderr)
        return self.popen.pid

    def wait(self):
        return self.popen.wait()

    def stop(self):
        # The following doesn't exist in python < 2.6, if you can believe it.
        #self.popen.terminate()
        os.kill(self.popen.pid, signal.SIGTERM)

    @property
    def exitCode(self):
        if self._exitCode == None:
            self._exitCode = self.wait()
        return self._exitCode

class XServer(Subprocess):
    def __init__(self, server="/usr/bin/Xorg", display=None, outfile=None,
                 xinitrc="/etc/X11/xinit/Xclients", resolution="1024x768x16"):
        """resolution is only used with Xvfb."""
        testBinary(server)
        self.server = server
        self._exitCode = None
        self.xinit = "/usr/bin/xinit"
        self.display = display
        self.outfile = outfile
        self.xinitrc = xinitrc
        self.resolution = resolution

    @staticmethod
    def findFreeDisplay():
        tmp = os.listdir('/tmp')
        pattern = re.compile('\.X([0-9]+)-lock')
        usedDisplays = []
        for file in tmp:
            match = re.match(pattern, file)
            if match: usedDisplays.append(int(match.groups()[0]))
        if not usedDisplays: return ':0'
        usedDisplays.sort()
        return ':' + str(usedDisplays[-1] + 1)

    @property
    def cmdList(self):
        if self.display is None:
            self.display = self.findFreeDisplay()
        cmd = []
        if self.xinit:
            cmd.append(self.xinit)
            if self.xinitrc: cmd.append(self.xinitrc)
            cmd.append('--')
        cmd.append(self.server)
        cmd.append(self.display)
        cmd.extend(['-ac', '-noreset'])
        if self.server.endswith('Xvfb'):
            cmd.extend(['-screen', '0', self.resolution])
            cmd.append('-shmem')
        return cmd

    def start(self):
        print >> self.outfile, ' '.join(self.cmdList)
        self.popen = subprocess.Popen(self.cmdList, stdout=self.outfile,
                                      stderr=self.outfile)
        return self.popen.pid

class Script(Subprocess):
    pass

class Session(object):

    cookieName = "DOGTAIL_SESSION_COOKIE"

    def __init__(self, sessionBinary, server, script, display=None,
                 quiet=False, scriptDelay=10, logout=True):

        testBinary(sessionBinary)
        self.sessionBinary = sessionBinary

        if quiet:
            self.outfile = open(os.devnull, 'w')
        else:
            self.outfile = None

        if server is None:
            # Indicates that no X server shall be started
            self.xserver = None
            self._reuseDisplay = display
        else:
            self.xserver = XServer(server, display, self.outfile)

        self.script = script
        self.scriptDelay = scriptDelay
        self.logout = logout
        self._cookie = None
        self._environment = None

    def start(self):
        # Start an X server if requested
        if self.xserver is None:
            xServerPid = None
        else:
            self.xinitrcFileObj = scratchFile('xinitrc')
            self.xserver.xinitrc = self.xinitrcFileObj.name
            self._buildXInitRC(self.xinitrcFileObj)
            xServerPid = self.xserver.start()
            time.sleep(self.scriptDelay)

        self.script.environ = self.environment
        scriptPid = self.script.start()

        return (xServerPid, scriptPid)

    @property
    def environment(self):
        def isSessionProcess(fileName):
            try:
                if os.path.realpath(path + 'exe') != self.sessionBinary: 
                    return False
            except OSError:
                return False
            pid = fileName.split('/')[2]
            if pid == 'self' or pid == str(os.getpid()): return False
            return True

        def getEnvDict(fileName):
            try: envString = open(fileName, 'r').read()
            except IOError: return {}
            envItems = envString.split('\x00')
            envDict = {}
            for item in envItems:
                if not '=' in item: continue
                k, v = item.split('=', 1)
                envDict[k] = v
            return envDict

        def isSessionEnv(envDict):
            if not envDict:
                return False

            if self.xserver is None:
                # We haven't launched any X server
                if self._reuseDisplay is None:
                    # No specific DISPLAY was requested so we're done here
                    return True
                else:
                    # A specific DISPLAY was requested
                    return envDict['DISPLAY'] == self._reuseDisplay
            else:
                # We're only interested in an X server instance that we
                # launched (i.e. has the right cookie)
                try:
                    return envDict[self.cookieName] == self.cookie
                except KeyError:
                    return False

        for path in glob.glob('/proc/*/'):
            if not isSessionProcess(path): continue
            envFile = path + 'environ'
            envDict = getEnvDict(envFile)
            if isSessionEnv(envDict):
                if self.xserver is None:
                    # Make sure the script output is in color on color
                    # terminals.  This is necessary if we are reusing a session
                    # that was launched by GDM which sets the TERM variable to
                    # "dumb".
                    envDict['TERM'] = os.environ['TERM']
                self._environment = envDict
                break
        if not self._environment:
            raise RuntimeError("Can't find our environment!")
        return self._environment

    def wait(self):
        self.script.wait()
        if self.xserver is None:
            return None
        else:
            return self.xserver.wait()

    def stop(self):
        try: self.script.stop()
        except OSError: pass
        if self.xserver is not None:
            self.xserver.stop()

    def attemptLogout(self):
        logoutScript = Script('dogtail-logout', self.environment, self.outfile,
                              self.outfile)
        logoutScript.start()
        logoutScript.wait()

    @property
    def cookie(self):
        if not self._cookie:
            self._cookie = "%X" % random.getrandbits(16)
        return self._cookie

    def _buildXInitRC(self, fileObj):
        if self.logout:
            logoutString = "; dogtail-logout"
        else:
            logoutString = ""
        lines = [
            "export %s=%s" % (self.cookieName, self.cookie),
            "gconftool-2 --type bool --set /desktop/gnome/interface/accessibility true",
            ". /etc/X11/xinit/xinitrc-common",
            "export %s" % self.cookieName,
            "exec -l $SHELL -c \"$CK_XINIT_SESSION $SSH_AGENT %s\"" % \
                    self.sessionBinary,
            ""]

        fileObj.write('\n'.join(lines).strip())
        fileObj.flush()
