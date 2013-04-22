from subol.sub2py import aeval, aexec
from subol.tokens import I
from subol import sub2py

from twisted.trial import unittest

import os, sys

from cStringIO import StringIO

class Compile(unittest.TestCase):
    def testReallySimple(self):
        self.assertEquals(aeval(1), 1)
        self.assertEquals(aeval('1'), '1')

    def testImport(self):
        ns = {}
        aexec([(I('import'), I('os'))], ns=ns)
        self.assertEquals(ns['os'], os)

    def testGetattr(self):
        ns = {'os': os}
        self.assertEquals(aeval(I('os.path.isdir'), ns=ns), os.path.isdir)
        self.assertRaises(AttributeError, aeval, I('os.pueoa'), ns=ns)

    def testSet(self):
        ns = {}
        aexec([(I('set'), I('foo'), 1)], ns=ns)
        self.assert_(ns.has_key('foo'))
        self.assertEquals(ns['foo'], 1)

    def testComparison(self):
        self.assert_(aeval((I('eq'), 4, 4)))
        self.assert_(aeval((I('lt'), 3, 4)))
        self.assert_(not aeval((I('gt'), 3, 4)))
        self.assert_(aeval((I('>='), 2, 2)))
        ns = {'os': os}
        self.assert_(aeval((I('is'), I('os'), I('os')), ns=ns))

    def testSyntaxy(self):
        self.assert_(aeval((I('=='), 4, 4)))
        ns = {}
        aexec([(I('='), I('foo'), 1)], ns=ns)
        self.assert_(ns.has_key('foo'))
        self.assertEquals(ns['foo'], 1)
        
    def testDef(self):
        ns = {}
        aexec([(I('def'), [I('foo')], "doc", [I('return'), 3])], ns=ns)
        self.assert_(ns.has_key('foo'))
        self.assertEquals(aeval((I('foo'),), ns=ns), 3)

    #testDef.todo = "guhhh there's a problem with the Return-izing code when the last thing in a function is not an Expression"

    def testReturnExpression(self):
        raise unittest.SkipTest("Return-izing a function when the last thing isn't an expression is broken")
        ns = {}
        aexec([(I('def'), [I('foo')], "doc", [I('='), I('x'), 3])], ns=ns)
        self.assert_(ns.has_key('foo'))
        self.assertEquals(aeval((I('foo'),), ns=ns), 3)

    def testPrint(self):
        io = StringIO()
        oldout = sys.stdout
        sys.stdout = io
        try:
            aexec([(I('println'), "hello")]) #if this fails, you'll want to remove the sys.stdout munging code to debug
        finally:
            sys.stdout = oldout
        self.assertEquals(io.getvalue(), 'hello\n') #if this fails, you'll want to remove the sys.stdout munging code to debug

