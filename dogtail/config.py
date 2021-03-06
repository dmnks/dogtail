"""
The configuration module.
"""
__author__ = "Zack Cerza <zcerza@redhat.com>, David Malcolm <dmalcolm@redhat.com>"

import os
import sys
import locale

class _Config(object):
    """
    Contains configuration parameters for the dogtail run.

    scratchDir(str):
    Directory where things like screenshots are stored.

    dataDir(str):
    Directory where related data files are located.

    logDir(str):
    Directory where dogtail.tc.TC*-generated logs are stored.

    scriptName(str) [Read-Only]:
    The name of the script being run.
    
    encoding(str)
    The encoding for text, used by dogtail.tc.TCString .

    actionDelay(float):
    The delay after an action is executed.

    typingDelay(float):
    The delay after a character is typed on the keyboard.

    runInterval(float):
    The interval at which dogtail.utils.run() and dogtail.procedural.run() 
    check to see if the application has started up.

    runTimeout(int):
    The timeout after which dogtail.utils.run() and dogtail.procedural.run()
    give up on looking for the newly-started application.
    
    searchBackoffDuration (float):
    Time in seconds for which to delay when a search fails.

    searchWarningThreshold (int):
    Number of retries before logging the individual attempts at a search.

    searchCutoffCount (int):
    Number of times to retry when a search fails.

    defaultDelay (float):
    Default time in seconds to sleep when delaying.

    childrenLimit (int):
    When there are a very large number of children of a node, only return
    this many, starting with the first.

    debugSearching (boolean):
    Whether to write info on search backoff and retry to the debug log.

    debugSleep (boolean):
    Whether to log whenever we sleep to the debug log.

    debugSearchPaths (boolean):
    Whether we should write out debug info when running the SearchPath
    routines.

    absoluteNodePaths (boolean):
    Whether we should identify nodes in the logs with long 'abcolute paths', or
    merely with a short 'relative path'. FIXME: give examples

    ensureSensitivity (boolean):
    Should we check that ui nodes are sensitive (not 'greyed out') before
    performing actions on them? If this is True (the default) it will raise
    an exception if this happens. Can set to False as a workaround for apps
    and toolkits that don't report sensitivity properly.

    debugTranslation (boolean):
    Whether we should write out debug information from the translation/i18n
    subsystem.

    blinkOnActions (boolean):
    Whether we should blink a rectangle around a Node when an action is
    performed on it.

    fatalErrors (boolean):
    Whether errors encountered in dogtail.procedural should be considered
    fatal. If True, exceptions will be raised. If False, warnings will be 
    passed to the debug logger.

    checkForA11y (boolean):
    Whether to check if accessibility is enabled. If not, just assume it is 
    (default True).

    logDebugToFile (boolean):
    Whether to write debug output to a log file.

    logDebugToStdOut (boolean):
    Whether to print log output to console or not (default True).
    """
    def _getScriptName(self):
        return os.path.basename(sys.argv[0]).replace('.py','')
    scriptName = property(_getScriptName)

    def _getEncoding(self):
        return locale.getpreferredencoding().lower()
    encoding = property(_getEncoding)

    defaults = {
            # Storage
            'scratchDir' : '/tmp/dogtail/',
            'dataDir' : '/tmp/dogtail/data/',
            'logDir' : '/tmp/dogtail/logs/',
            'scriptName' : scriptName.fget(None),
            'encoding' : encoding.fget(None),
            'configFile' : None,
            'baseFile' : None,

            # Timing and Limits
            'actionDelay' : 1.0,
            'typingDelay' : 0.075,
            'runInterval' : 0.5,
            'runTimeout' : 30,
            'searchBackoffDuration' : 0.5,
            'searchWarningThreshold' : 3,
            'searchCutoffCount' : 20,
            'defaultDelay' : 0.5,
            'childrenLimit' : 100,

            # Debug
            'debugSearching' : False,
            'debugSleep' : False,
            'debugSearchPaths' : False,
            'logDebugToStdOut' : True,
            'absoluteNodePaths' : False,
            'ensureSensitivity' : False,
            'debugTranslation' : False,
            'blinkOnActions' : False,
            'fatalErrors' : False,
            'checkForA11y' : True,

            # Logging
            'logDebugToFile' : True
    }

    options = {}

    invalidValue = "__INVALID__"

    def __init__(self):
        _Config.__createDir(_Config.defaults['scratchDir'])
        _Config.__createDir(_Config.defaults['logDir'])
        _Config.__createDir(_Config.defaults['dataDir'])

    def __setattr__(self, name, value):
        if not config.defaults.has_key(name):
            raise AttributeError, name + " is not a valid option."

        elif _Config.defaults[name] != value or \
                _Config.options.get(name, _Config.invalidValue) != value:
            if 'Dir' in name:
                _Config.__createDir(value)
                if value[-1] != os.path.sep: value = value + os.path.sep
            elif name == 'logDebugToFile':
                import logging
                logging.debugLogger = logging.Logger('debug', value)
            _Config.options[name] = value

    def __getattr__(self, name):
        try: return _Config.options[name]
        except KeyError:
            try: return _Config.defaults[name]
            except KeyError: raise AttributeError, name + \
                    " is not a valid option."

    def __createDir(cls, dirName, perms = 0777):
        """
        Creates a directory (if it doesn't currently exist), creating any 
        parent directories it needs.

        If perms is None, create with python's default permissions.
        """
        dirName = os.path.abspath(dirName)
        #print "Checking for %s ..." % dirName,
        if not os.path.isdir(dirName):
            if perms: 
                umask = os.umask(0)
                os.makedirs(dirName, perms)
                os.umask(umask)
            else: os.makedirs(dirName)
    __createDir = classmethod(__createDir)

    def load(self, dict):
        """
        Loads values from dict, preserving any options already set that are not overridden.
        """
        _Config.options.update(dict)

    def     reset(self):
        """
        Resets all settings to their defaults.
        """
        _Config.options = {}


config = _Config()

if __name__ == '__main__':
    anyFailed = False
    def failOrPass(failure, description):
        if failure:
            anyFailed = True
            print "FAILED: " + description
        else: print "PASSED: " + description

    # BEGIN tests

    failure = False
    for option in config.defaults.keys():
        failure = failure or not (getattr(config, option) == \
                config.defaults[option])
        print failure, option, getattr(config, option), config.defaults[option]
    failOrPass(failure, "Reading all default values")

    failure = True
    failure = config.ensureSensitivity != config.defaults['ensureSensitivity']
    config.ensureSensitivity = False
    failure = failure or config.ensureSensitivity == True
    config.ensureSensitivity = True
    failure = failure or config.ensureSensitivity != True
    failOrPass(failure, "Setting ensureSensitivity")

    failure = True
    failure = not os.path.isdir(config.defaults['scratchDir'])
    failure = failure or not os.path.isdir(config.defaults['logDir'])
    failure = failure or not os.path.isdir(config.defaults['dataDir'])
    failOrPass(failure, "Looking for default directories")

    failure = True
    config.scratchDir = '/tmp/dt'
    failure = not os.path.isdir('/tmp/dt')
    config.logDir = '/tmp/dt_log/'
    failure = failure or not os.path.isdir('/tmp/dt_log/')
    config.dataDir = '/tmp/dt_data'
    failure = failure or not os.path.isdir('/tmp/dt_data')
    failOrPass(failure, "Changing default directories")

    # END tests

    if anyFailed: sys.exit(1)
