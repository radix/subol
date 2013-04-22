# XXX Still not sure if it's cool to have the objects do ASTy things.

# TODO: Token class which only and all tokens subclass

from safelisp import context
from safelisp import environment as E

__metaclass__ = type

class SLObject:
    def __init__(self):
        self.__sl_dict__ = {}

    def __str__(self):
        if self.__sl_dict__.has_key('__str__'):
            return self.__sl_dict__['__str__'].callFunc(context.get('SL-interp')).pyvalue
        return object.__str__(self)

    def sl_getAttribute(self, name):
        if not name in self.__sl_dict__:
            raise AttributeError(name)
        return self.__sl_dict__[name]

    def sl_setAttribute(self, name, value):
        self.__sl_dict__[name] = value
        return value


def py2SLO(o):
    """
    *non*-recursively converts a Python object to a SafeLisp PythonWrapper object.
    """
    for x in PythonWrapperBase.__subclasses__():
        if isinstance(o, x.pytype):
            return x(o)


def form2code(form):
    """
    This is used for printing forms in tracebacks. Maybe I should
    remember the line in the source file and use it...?
    """
    o = simplify(form)
    l = ['(']
    for x in o:
        if l[-1] != '(':
            l.append(' ')
        if isinstance(x, Identifier):
            l.append(x.name)
        elif isinstance(x, list):
            l.append(form2code(x))
        else:
            l.append(str(x))
    l.append(')')
    return ''.join(l)
        
            

def simplify(form):
    """
    Recursively converts a SafeLisp object into a Python object.

    Useful for unit testing, and writing SafeLisp extensions in Python.
    """
    if isinstance(form, PythonWrapperBase):
        form = form.pyvalue
    if isinstance(form, (list, tuple)):
        return map(simplify, form)
    if isinstance(form, dict):
        return dict([(simplify(k), simplify(v)) for k,v in form.items()])
    return form



class PythonWrapperBase(SLObject):
    pytype = object
    def __init__(self, pyvalue, lineno=None):
        SLObject.__init__(self)
        assert isinstance(pyvalue, self.pytype), "%s isn't a %s!!!" % (pyvalue, self.pytype)
        self.lineno = lineno
        self.pyvalue = pyvalue

    def __str__(self):
        return "<%s %r>" % (self.__class__.__name__, self.pyvalue)

    __repr__ = __str__


    def __hash__(self):
        return hash(self.pyvalue)


    def __eq__(self, other):
        return hasattr(other, 'pyvalue') and self.pyvalue == other.pyvalue



class Number(PythonWrapperBase):
    pytype = (int, float, long)
    #%s is better than %r for numbers. L.
    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self.pyvalue)



class String(PythonWrapperBase):
    pytype = str



class List(PythonWrapperBase):
    pytype = list

    def sl_getAttribute(self, name):
        if name == 'append':
            return self.pyvalue.append
        return PythonWrapperBase.sl_getAttribute(self, name)


    def __sl_index__(self, i):
        if not isinstance(i, Number):
            raise ValueError("Need a number, dogg")
        return self.pyvalue[i.pyvalue]



class Dict(PythonWrapperBase):
    pytype = dict
    def __sl_index__(self, k):
        return self.pyvalue[k]



class Identifier(SLObject):
    def __init__(self, name, lineno=None):
        self.name = name
        self.lineno = lineno

    def __str__(self):
        return "I:<%s>" % self.name

    __repr__ = __str__

    def __eq__(self, other):
        return hasattr(other, 'name') and self.name == other.name

    def __hash__(self):
        return hash(self.name)

I = Identifier

class BasicToken:
    def __init__(self, lineno=None):
        self.lineno = lineno

    def __eq__(self,o):
        return self.__class__ == o.__class__
    def __hash__(self):
        return hash(self.__class__)

class OpenBracket(BasicToken): pass
class CloseBracket(BasicToken): pass

class OpenParen(BasicToken): pass
class CloseParen(BasicToken): pass

class OpenCurly(BasicToken): pass
class CloseCurly(BasicToken): pass

class NewLine(BasicToken): pass
class Bang(BasicToken): pass
class Hash(BasicToken): pass
class Colon(BasicToken): pass
class Dot(BasicToken): pass


## woo ##



class ParameterError(Exception):
    pass
class ApplicationError(ParameterError):
    pass

class Function(SLObject):
    curform = None
    def __init__(self, name, lambdalist, body, env):
        SLObject.__init__(self)
        self.name = name
        # A function captures its environment! w00t!
        self.env = env
        self._sanityCheck(lambdalist)
        self.lambdalist = lambdalist
        self.body = body

    def _sanityCheck(self, lambdalist):
        for i,n in enumerate(lambdalist):
            if n.name[0] == '&':
                if i != len(lambdalist)-1:
                    raise ParameterError("A & argument *must* be the last argument.")

    def makeBindings(self, values):
        # this is kinda bleghy
        d = {}
        enum = enumerate(self.lambdalist)
        i = -1 # arithmetic trick!
        while 1:
            try:
                i, name = enum.next()
            except StopIteration:
                if i == len(values)-1:
                    break
                raise ApplicationError("Too many arguments. Expected %s, got more than that!" % (i+1))
            if name.name[0] == '&':
                d[name.name[1:]] = List(list(values[i:]))
                return d
            try:
                d[name.name] = values[i]
            except IndexError:
                raise ApplicationError("Not enough arguments for %s(%s). Expected %s, got %s." % (self.name.pyvalue, self.lambdalist, len(self.lambdalist), i))

        return d

    def callFunc(self, interp, args=None):
        #print "appending", self
        interp.frames.append(self)
        if args is not None:
            bindings = self.makeBindings(args.pyvalue)
        else:
            bindings = {}
        newEnv = E.pushFrame(self.env, bindings)
        r = None
        for form in self.body:
            self.curform = form
            r = interp.evalForm(form, newEnv)
        #print "popping", self
        interp.frames.pop()
        return r

    def _get_name(self):
        r = self.__sl_dict__.get('name', String('<function>'))
        return r
    def _set_name(self, value):
        self.__sl_dict__['name'] = value
    name = property(_get_name, _set_name)

##    def __str__(self):
##        return "<Function %s at %s>" % (self.name, id(self))

##    __repr__ = __str__

class Macro(SLObject):
    def __init__(self, name, lambdalist, body, env):
        SLObject.__init__(self)
        self.name = name
        self.expand = Function('macro:' + name.pyvalue, lambdalist, body, env).callFunc
    
    def callMacro(self, interp, env, args):
        funresult = self.expand(interp, List(args))
        #print "FUNRESULt", simplify(funresult)
        return interp.evalForm(funresult, env)

    def _get_name(self):
        return self.__sl_dict__.get('name', String('<macro>'))
    def _set_name(self, value):
        self.__sl_dict__['name'] = value
    name = property(_get_name, _set_name)
    
