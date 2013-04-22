import sys, operator, os

from safelisp import parse
from safelisp import objects as O
from safelisp import environment as E
from safelisp import context

__metaclass__ = type



## Evaluation ##

def print_traceback(interp):
    if interp.frames:
        print "----------------------------------------------------------"
        print "An error occured. Traceback follows, innermost frame last."
        print "=========================================================="
    for x in interp.frames:
        print "    In %s, line %s" % (x.name.pyvalue, x.curform and x.curform.lineno)
        print "       ", O.form2code(x.curform)
    kl, inst = sys.exc_info()[:2]
    print "%s: %s" % (kl.__name__, inst)


def evalString(s, env=None, maxInstructions=None):
    return defaultInterpreter().evalString(s, env, maxInstructions)

class SecurityError(Exception):
    pass

class TooManyInstructions(SecurityError):
    pass

class UnevaluableError(ValueError):
    pass


def defaultEnvironment():
    # XXX modules
    #from t.p.util.sibpath
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.join('library', 'builtins.slisp'))
    from safelisp import builtins
    e = E.environment(builtins.getFunctions())
    defaultInterpreter().evalString(open(path).read(), e)
    return e


def defaultInterpreter():
    from safelisp import specials
    i = Interpreter()
    i.addSpecials(specials.getSpecials())
    return i


class Interpreter:

    maxInstructions = None

    def __init__(self):
        self.frames = []
        self.specials = {}

    def evalString(self, s, env=None, maxInstructions=None):
        p = parse.Parser()
        if env is None:
            env = defaultEnvironment()
        r = None
        for form in p.parse(s):
            r = self.eval(form, env, maxInstructions)
        return r


    def eval(self, form, env, maxInstructions=None):
        self.maxInstructions = maxInstructions
        self.instructions = 0
        try:
            try:
                return context.call({'SL-interp': self}, 
                                    self.evalForm, form, env)
            except:
                # XXX This is _really_ not how it should be.
                # Firstly, the thing that handles Python exceptions
                # should be separate from the thing that handles
                # Safelisp exceptions. Of course, that implies that
                # Safelisp has its _own_ exception system. Then, of
                # course, the arguments to *exc-handler* should be a
                # Safelisp-representation of the exception and
                # traceback objects.
                exch = E.lookup(env, '*exc-handler*')
                if exch:
                    if isinstance(exch, O.Function):
                        stuff = sys.exc_info()
                        errorclass = stuff[0].__name__
                        errormessage = str(stuff[1])
                        frames = self.frames[:]
                        context.call({'SL-interp': self},
                                     exch.callFunc,
                                     self, 
                                     O.List([errorclass, errormessage, frames]))
                    else:
                        exch(self)
                    self.frames = []
                else:
                    self.frames = []
                    raise
        finally:
            self.maxInstructions = None

    def evalForm(self, form, env):
        """
        Evaluate a form in an environment
        """
        assert context.get('SL-interp', None) is not None, "Only call evalForm from within eval!"
        if self.maxInstructions:
            self.instructions += 1
            if self.instructions > self.maxInstructions:
                raise TooManyInstructions("Your limit is %s, buddy." % self.maxInstructions)

        # XXX This code is *riddled* with isinstance. What's a better solution?

        if not isinstance(form, O.SLObject):
            raise UnevaluableError("I cannot evaluate %s." % form)

        if isinstance(form, O.Identifier):
            return E.lookup(env, form.name)

        if not isinstance(form, O.List):
            return form


        if isinstance(form, O.List):
            value = form.pyvalue
            if not value:
                raise SyntaxError("Empty call.")
            if isinstance(value[0], O.Identifier):
                name = value[0].name
                func = self.specials.get(name, None)
                if func:
                    return func(self, form, env)

            func = self.evalForm(value[0], env)
            #print "GOT THE FUNC", func, "FROM", value
            if isinstance(func, O.Macro):
                return func.callMacro(self, env, value[1:])

            # Must be a function call: LispEvaluate the
            # elements of the list
            args = [self.evalForm(x, env) for x in value[1:]]

            if isinstance(func, O.Function):
                return func.callFunc(self, O.List(args))

            # must be a python extension...
            r = context.call({'SL-env': env}, func, *args)
            return r

        raise RuntimeError("This is a bug. What the heck is %s?" % repr(form))


    def addSpecials(self, d):
        # d = {'while': <function special_while>}
        self.specials.update(d)




