from twisted.trial import unittest

from safelisp import environment as E


class EnvironmentTest(unittest.TestCase):

    def setUp(self):
        self.init = {'x': 1}
        self.env = E.environment(self.init)

    def testLookup(self):
        self.assertEquals(E.lookup(self.env, 'x'), 1)

    def testLookupInner(self):
        second = {'y': 2}
        env = E.pushFrame(self.env, second)
        self.assertEquals(E.lookup(env, 'y'), 2)
    
    def testNameError(self):
        self.assertRaises(NameError, E.lookup, self.env, 'z')

    def testSettingNew(self):
        """
        Setting a non-existent variable should die.
        """
        new = {}
        env = E.pushFrame(self.env, new)
        self.assertRaises(NameError, E.set, env, 'a', 3.14)
#         self.assertEquals(E.lookup(env, 'a'), 3.14)
#         self.assertRaises(NameError, E.lookup, self.env, 'a')

    def testSettingOuterOld(self):
        """
        Setting x should change it in the frame where x was
        originally defined.
        """
        E.set(self.env, 'x', 3)
        self.assertEquals(self.init['x'], 3)

    def testDefinition(self):
        """
        Defining z should add it to the innermost frame.
        """
        new = {}
        env = E.pushFrame(self.env, new)
        E.define(env, 'z', 4)
        self.assertEquals(new['z'], 4)

    def testDefinitionShadowing(self):
        """
        Defining x should change it in the innermost frame and not
        affect the binding of x in the outer frames.
        """
        new = {}
        env = E.pushFrame(self.env, new)
        E.define(env, 'x', 5)
        self.assertEquals(self.init['x'], 1)
        self.assertEquals(new['x'], 5)
