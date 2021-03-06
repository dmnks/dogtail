# -*- coding: utf-8 -*-
"""Test Case magic

Author: Ed Rousseau <rousseau@redhat.com>"""
__author__ = "Ed Rousseau <rousseau@redhat.com>"

import string
import sys
import os
import re
import time
import datetime
import os.path
from config import config
from logging import ResultsLogger, TimeStamp, debugLogger
from PIL import Image, ImageChops, ImageStat


class TC(object):
    """
    The Test Case Superclass
    """
    logger = ResultsLogger()
    def __init__(self):
        self.encoding = config.encoding
        # ascii + unicode. 8 bit extended char has been ripped out
        self.supportedtypes = ("ascii", "utf-8", "utf-16", "utf-16-be", "utf-16-le", "unicode-escape", "raw-unicode-escape",
        "big5", "gb18030", "eucJP", "eucKR", "shiftJIS")

    # String comparison function
    def compare(self, label, baseline, undertest, encoding=config.encoding):
        """
        Compares 2 strings to see if they are the same. The user may specify
        the encoding to which the two strings are to be normalized for the
        comparison. Default encoding is the default system encoding.
        Normalization to extended 8 bit charactersets is not supported.

        When the origin of either baseline or undertest is a text file whose
        encoding is something other than ASCII, it is necessary to use
        codecs.open() instead of open(), so the file's encoding may be
        specified.
        """
        self.label = label.strip()
        self.baseline = baseline
        self.undertest = undertest
        for string in [self.baseline, self.undertest]:
            try: string = unicode(string, 'utf-8')
            except TypeError: pass
        self.encoding = encoding

        # Normalize the encoding type for the comparaison based on self.encoding
        if self.encoding in self.supportedtypes:
            self.baseline = (self.baseline).encode(self.encoding)
            self.undertest = (self.undertest).encode(self.encoding)
            # Compare the strings
            if self.baseline == self.undertest:
                self.result = {self.label: "Passed"}
            else:
                self.result = {self.label: "Failed - " + self.encoding + " strings do not match. " + self.baseline + " expected: Got " + self.undertest}
            # Pass the test result to the ResultsLogger for writing
            TC.logger.log(self.result)
            return self.result

        else:
            # We should probably raise an exception here
            self.result = {self.label: "ERROR - " + self.encoding + " is not a supported encoding type"}
            TC.logger.log(self.result)
            return self.result


# String Test Case subclass
class TCString(TC):
    """
    String Test Case Class
    """
    def __init__(self):
        TC.__init__(self)

# Image test case subclass
class TCImage(TC):
    """
    Image Test Case Class.
    """
    def compare(self, label, baseline, undertest):
        for _file in (baseline, undertest):
            if type(_file) is not unicode and type(_file) is not str:
                raise TypeError("Need filenames!")
        self.label = label.strip()
        self.baseline = baseline.strip()
        self.undertest = undertest.strip()
        diffName = TimeStamp().fileStamp("diff") + ".png"
        self.diff = os.path.normpath(
                os.path.sep.join((config.scratchDir, diffName)))

        self.baseImage = Image.open(self.baseline)
        self.testImage = Image.open(self.undertest)
        try:
            if self.baseImage.size != self.testImage.size: 
                self.result = {self.label: "Failed - images are different sizes"}
                raise StopIteration

            self.diffImage = ImageChops.difference(self.baseImage, 
                    self.testImage)
            self.diffImage.save(self.diff)
            result = False
            for stat in ('stddev', 'mean', 'sum2'):
                for item in getattr(ImageStat.Stat(self.diffImage), stat):
                    if item: 
                        self.result = {self.label: "Failed - see %s" % 
                                self.diff}
                        raise StopIteration
                    else: result = True
        except StopIteration:
            result = False

        if result: self.result = {self.label: "Passed"}

        TC.logger.log(self.result)
        return self.result


class TCNumber(TC):
    """
    Number Comparaison Test Case Class
    """
    def __init__(self):
        TC.__init__(self)
        self.supportedtypes = ("int", "long", "float", "complex", "oct", "hex")

    # Compare 2 numbers by the type provided in the type arg
    def compare(self, label, baseline, undertest, type):
        """
        Compares 2 numbers to see if they are the same. The user may specify
        how to normalize mixed type comparisons via the type argument.
        """
        self.label = label.strip()
        self.baseline = baseline
        self.undertest = undertest
        self.type = type.strip()

        # If we get a valid type, convert to that type and compare
        if self.type in self.supportedtypes:
            # Normalize for comparison
            if self.type == "int":
                self.baseline = int(self.baseline)
                self.undertest = int(self.undertest)
            elif self.type == "long":
                self.baseline = long(self.baseline)
                self.undertest = long(self.undertest)
            elif self.type == "float":
                self.baseline = float(self.baseline)
                self.undertest = float(self.undertest)
            else:
                self.baseline = complex(self.baseline)
                self.undertest = complex(self.undertest)

            #compare
            if self.baseline == self.undertest:
                self.result = {self.label: "Passed - numbers are the same"}
            else:
                self.result = {self.label: "Failed - " + str(self.baseline) + " expected: Got " + str(self.undertest)}
            TC.logger.log(self.result)
            return self.result
        else:
            self.result = {self.label: "Failed - " + self.type + " is not in list of supported types"}
            TC.logger.log(self.result)
            return self.result

class TCBool(TC):
    def __init__(self): pass

    def compare(self, label, _bool):
        """
        If _bool is True, pass.
        If _bool is False, fail.
        """
        if type(_bool) is not bool: raise TypeError
        if _bool: result = {label: "Passed"}
        else: result = {label: "Failed"}
        TC.logger.log(result)

from tree import Node
class TCNode(TC):
    def __init__(self): pass

    def compare(self, label, baseline, undertest):
        """
        If baseline is None, simply check that undertest is a Node.
        If baseline is a Node, check that it is equal to undertest.
        """
        if baseline is not None and not isinstance(baseline, Node): 
            raise TypeError

        if not isinstance(undertest, Node):
            result = {label: "Failed - %s is not a Node" % undertest}
        elif baseline is None:
            result = {label: "Passed - %s is a Node" % undertest}
        elif isinstance(baseline, Node):
            if baseline == undertest: 
                result = {label: "Passed - %s == %s" % (baseline, undertest)}
            else: result = {label: "Failed - %s != %s" % (baseline, undertest)}
        TC.logger.log(result)


if __name__ == '__main__':
    # import the test modules
    import codecs
    from utils import *

    # Set up vars to use to test TC class
    baseline = "test"
    undertest = "test"
    label = "unit test case 1.0"
    encoding = "utf-8"
    result = {}

    # Create the TC instance
    case1 = TC()

    # Fire off the compaison
    result = case1.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - passed
    print(result)

    # Reset variables for failure path
    undertest = "testy"
    encoding = "utf-8"
    result = {}
    label = "unit test case 1.1"

    # Compare again
    result = case1.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - failure
    print(result)

    # Create a TCString instance
    case2 = TCString()

    # Load our variables for this test
    label = " unit test case 2.0"
    encoding = "utf-8"
    baseline = u"groß"
    undertest = u"gro\xdf"
    result = {}

    # Fire off a UTF-8 compare
    result = case2.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - passed
    print(result)

    # Fire the test for ASCII converted to UTF-8 testing
    label = " unit test case 2.1"
    encoding = "utf-8"
    baseline = "please work"
    undertest = "please work"
    result = {}

    result = case2.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - passed
    print(result)

    # Reset variables for an out of range encoding type
    label = " unit test case 2.2"
    encoding = "swahilli"
    baseline = "please work"
    undertest = "please work"
    result = {}

    result = case2.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - Error - not supported
    print(result)

    # Reset variables for unmatched utf-8 strings
    label = " unit test case 2.3"
    encoding = "utf-8"
    baseline = u"groß"
    undertest = "nomatch"
    result = {}

#       result = case2.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - failure
    print(result)

    # Reset variables for inherited TC base compare
    label = " unit test case 2.4"
    baseline = "This is inhereited"
    undertest = "This is inhereited"
    encoding = "utf-8"
    result = {}

    result = case2.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - Passed
    print(result)


    # Include real CJKI (UTF-8) charcters for string compare
    # For this first test case, we are comparing same JA characters
    label = " unit test case 2.5"
    encoding = "utf-8"
    baseline = u"あか"
    undertest = u"あか"
    result = {}

    result = case2.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - Passed
    print(result)


    # Testing different JA characters
    label = " unit test case 2.6"
    encoding = "utf-8"
    baseline = u"あか"
    undertest = u"元気"
    result = {}

    result = case2.compare(label, baseline, undertest, encoding)

    # Print the result - should be label - Failed
    print(result)



    # Test the timestamper class
    # Create a new timestamp instance
    # Print the file format time
    stamp1 = TimeStamp()
    presently = stamp1.fileStamp("filestamp")

    # Print - should be filenameYYYYMMDD with local systems date
    print presently

    # Make a stamp entry
    entry = stamp1.entryStamp()

    # Print the entrystamp - should be YYYY-MM-DD_HH:MM:SS with local system time
    print entry

    # Copmare different colors
    label = "unit test case 3.0"
    baseline = "../examples/data/20w.png"
    undertest = "../examples/data/20b.png"
    result = {}

    # Create a TCImage instance
    case3 = TCImage()

    # Fire off the compare
    result = case3.compare(label, baseline, undertest)

    # Print the result Should be label - Failed
    print result

    # Compare different sizes
    label = "unit test case 3.1"
    baseline = "../examples/data/20w.png"
    undertest = "../examples/data/10w.png"
    result = {}

    # Fire off the compare
    result = case3.compare(label, baseline, undertest)

    # Print the result Should be label - Failed
    print result

    # Compare the same image
    label = "unit test case 3.2"
    baseline = "../examples/data/10w.png"
    undertest = "../examples/data/10w.png"
    result = {}

    # Fire off the compare
    result = case3.compare(label, baseline, undertest)

    # Print the result Should be label - Passed
    print result

    # Number comparison tests
    label = "unit test case 4.0"
    baseline = 42
    undertest = 42
    type = "int"
    result = {}

    # Make a TCNumber instance
    case4 = TCNumber()

    # Make a simple int compare
    result = case4.compare(label, baseline, undertest, type)

    # Should be Passed
    print result

    # Now make the int fail
    label = "unit test case 4.1"
    undertest = 999
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should fail
    print result

    # Now long pass
    label = "unit test case 4.2"
    baseline = 1112223334445556667778889990L
    undertest = 1112223334445556667778889990L
    type = "long"
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should pass
    print result

    # Float Pass
    label = "unit test case 4.3"
    baseline = 99.432670
    undertest = 99.432670
    type = "float"
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should pass
    print result

    # Complex pass
    label = "unit test case 4.4"
    baseline = 67+3j
    undertest = 67+3j
    type = "complex"
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should pass
    print result

    # Octal pass
    label = "unit test case 4.5"
    baseline = 0400
    undertest = 0400
    type = "oct"
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should pass
    print result

    # Hex pass
    label = "unit test case 4.6"
    baseline = 0x100
    undertest = 0x100
    type = "hex"
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should pass
    print result

    # Conversion pass - pass in equivalent hex and octal but compare as int
    label = "unit test case 4.7"
    baseline = 0x100
    undertest = 0400
    type = "int"
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should pass
    print result

    # Give a bogus type
    label = "unit test case 4.8"
    type = "face"
    result = {}

    result = case4.compare(label, baseline, undertest, type)

    # Should fail - unsupported type
    print result
