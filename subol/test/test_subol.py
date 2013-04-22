from subol import imhook
if not imhook.installed:
    imhook.installImportHook()

from twisted.trial import unittest

from subol import sub2py

class TEST(unittest.TestCase):
    def testImportHook(self):
        from subol.test import foo
        self.assertEquals(foo.x, 2)
        from subol.test import subolpackage
        self.assertEquals(subolpackage.x, "yay, package")
        self.assert_(not hasattr(subolpackage, 'toot'))
        from subol.test.subolpackage import toot
        self.assert_(hasattr(subolpackage, 'toot'))
        self.assertEquals(toot.y, "this is subolpackage.toot")

try:
    from subol.test.suboltest import *
except:
    import traceback; traceback.print_exc()
