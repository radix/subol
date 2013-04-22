Atom = (str, unicode, int, float, long)
Form = (list, tuple)

__metaclass__ = type

class Identifier:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "I:<%s>" % self.name

    __repr__ = __str__

    def __eq__(self, other):
        if not hasattr(other, 'name'):
            return False
        return self.name == other.name

I = Identifier

class Unknown:
    def __init__(self, const):
        self.const = const

    def __str__(self):
        return "U:<%s>" % self.const

    __repr__ = __str__

class OpenBracket: pass
class CloseBracket: pass

class OpenParen: pass
class CloseParen: pass

class OpenCurly: pass
class CloseCurly: pass

class Indent: pass
class Dedent: pass

class NewLine: pass
class Bang: pass
class Hash: pass
class Colon: pass
class Dot: pass
