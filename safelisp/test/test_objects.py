from twisted.trial import unittest

from safelisp import builtins, objects, builtins

class ObjectStuff(unittest.TestCase):
    def test_getattrError(self):
        slo = objects.SLObject()
        self.assertRaises(AttributeError, 
                          builtins.func_getattr, slo, objects.String("hi"))

    def test_setattr(self):
        slo = objects.SLObject()
        builtins.func_setattr(slo, objects.String("hi"), "there")
        self.assertEquals(builtins.func_getattr(slo, objects.String("hi")),
                          "there")

    def test_customBehavior(self):
        getattrs = []
        setattrs = []
        class WonkySlo(objects.SLObject):
            def sl_getAttribute(self, name):
                getattrs.append(name)
            def sl_setAttribute(self, name, value):
                setattrs.append((name, value))

        wslo = WonkySlo()
        builtins.func_getattr(wslo, objects.String("ueoa"))
        builtins.func_setattr(wslo, objects.String("yea"), "baby")
        self.assertEquals(getattrs, ["ueoa"])
        self.assertEquals(setattrs, [("yea", "baby")])
        
