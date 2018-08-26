"""

This was copied from Subol's parser. It's much simplified: No
indentation garbage, no newline tokens. We still probably don't need
all the features it gives us (e.g., is separation of tokenization and
parsing really necessary?).

"""


from cStringIO import StringIO
import string, operator

NUMBER_D = ''.join(map(str, range(10)))
FLOAT_D = NUMBER_D + '.'
INITID_D = string.letters + '_=+-<>/*!?&'
ID_D = INITID_D + NUMBER_D + '.' #XXX dot bad

literals = (str, unicode, int, float, long)

from safelisp import objects as O

class ExpectedMore(SyntaxError):
    """EOF in the middle of a string/list; Expected indented block; etc"""
    pass


class AbstractParser(object):
    """
    I'm worthless on my own, but I define a bunch of utilities.
    """
    def __init__(self):
        self.readtable = {}
        self.tokensets = {}
        self.tokentypes = {}
        self.lineno = 1

    def syntaxError(self, msg, result, etype=SyntaxError):
        raise etype('Syntax error at line %s, already parsed: %s\n%s' % (self.lineno, result, msg))

    def addTokenSet(self, tokens, name):
        for c in tokens:
            self.tokensets[c] = name

    def addTokenType(self, type, method):
        """
        This type has to be the direct type of the object, not a
        superclass of it. I.e., token.__class__ is type.
        """
        self.tokentypes[type] = method

    def parseDefault(self, c, stream, result):
        raise NotImplementedError("UEO")

    def parse(self, code):
        """
        I always return a list.
        """
        result = []
        s = Stream(StringIO(code))
        while 1:
            try:
                self.read(s, result=result)
            except EOFError:
                break
        return result

    def read(self, stream, c=None, result=None):
        """
        Parse a stream. If `c' is not given, a token will be read from
        the stream. If `result' is not given, a new AST object will be
        created.

        I delegate the actual parsing to other handlers. The method
        for finding handlers is thus:

        1) look up the token in the readtable
        2) Failing that, if the token was associated with a tokenset,
           look the associated tokenset up in the readtable
        3) Failing that, see if the type of the token has a handler.
        4) Failing *that*, use parseDefault.
        """
        if c is None:
            c = stream.read()
        if result is None:
            result = []

        # Find an appropriate method to handle this token

        # 1
        thingy = self.readtable.get(c)

        # 2
        if thingy is None:
            type = self.tokensets.get(c, c)
            thingy = self.readtable.get(type)

        if thingy is not None:
            thingy = thingy[-1]

        # 3
        if thingy is None:
            thingy = self.tokentypes.get(c.__class__, None)

        # 4
        if not thingy:
            thingy = self.parseDefault

        thingy(c, stream, result)
        return result


    def addReaderMacro(self, c, fun):
        self.readtable.setdefault(c, []).append(fun)

##    def removeReaderMacro(self, c, fun):
##        macros = self.readtable[c]
##        for i in range(len(macros), -1, -1):
##            if macros[i] is fun:
##                del macros[i]
##                return
##        raise KeyError("%s not found in %s's macro stack" % (fun, c))



class Parser(AbstractParser):
    def __init__(self):
        AbstractParser.__init__(self)

        for tok,func in [(O.OpenParen, self.parseList),
                         (O.OpenBracket, self.parseMakeList),
                         (O.Colon, self.parseGetattr),
                         #(O.Bang, self.parseAddReaderMacro),
                         #(O.OpenCurly, self.parseInfix),
                         #(O.Dot, lambda *args: None),
                         #(O.Dot, self.parseDot),
                         #(O.NewLine, self.parseNewLine),
                         ]:
            self.addTokenType(tok, func)

        def passThrough(c,s,r):
            return self.addItem(r,c)
        for tok in (O.Number, O.String):
            self.addTokenType(tok, passThrough)

    def parse(self, code):
        result = []
        tokens = Tokenizer().parse(code)
        s = Stream(tokens)
        while 1:
            try:
                self.read(s, result=result)
            except EOFError:
                break
        return result


    def addItem(self, result, item):
        #item.lineno = self.lineno
        result.append(item)


    def parseDefault(self, c, stream, result):
        if isinstance(c, O.Identifier):
            self.addItem(result, c)
        else:
            self.syntaxError("Got an unexpected %r!" % c, result)


    def parseList(self, c, stream, result, delim=O.CloseParen):
        r = []
        origi = stream.i
        origc = c
        while 1:
            try:
                c = stream.read()
            except EOFError:
                self.syntaxError("EOF in the middle of a list, expecting a %r to close the %r at pos #%s" % (delim, origc, origi), result, ExpectedMore)
            if isinstance(c, delim):
                break
            self.read(stream, c, r)
        self.addItem(result, O.List(r, lineno=c.lineno))


    def parseMakeList(self, c, stream, result, delim=O.CloseBracket):
        self.parseList(c, stream, result, delim=delim)
        result[-1].pyvalue.insert(0, O.I('vec', lineno=c.lineno))

    def parseGetattr(self, c, stream, result):
        id = stream.read()
        lhs = result.pop(-1)
        if not isinstance(id, O.I):
            self.syntaxError("Right hand side of a ':' must be an identifier.", result)
        result.append(O.List([O.I('getattr', lineno=c.lineno), lhs, O.String(id.name, id.lineno)], lineno=c.lineno))


class Tokenizer(AbstractParser):
    """
    I'll return a flat AST containing tokens!
    """

    lineno = 1

    def __init__(self):
        AbstractParser.__init__(self)
        self.readtable = {}
        self.indents = [] # list of numbers of indents

        plainTokens = {'[': O.OpenBracket,
                       ']': O.CloseBracket,
                       '(': O.OpenParen,
                       ')': O.CloseParen,
                       #'!': O.Bang,
                       ':': O.Colon,
                       '{': O.OpenCurly,
                       '}': O.CloseCurly,
                       '\n': O.NewLine,
                       }

        for c in plainTokens:
            def tokenizeSimple(c, stream, result):
                self.addToken(result, plainTokens[c](lineno=self.lineno))
            self.addReaderMacro(c, tokenizeSimple)

        for c, f in [('"', self.parseString),
                     ('numbers', self.parseNumber),
                     ('identifier', self.parseIdentifier),
                     ('#', self.parseComment),
                     (';', self.parseComment),
                     ('-', self.parseNegative),
                     ('\n', self.parseNewLine),
                     ]:
            self.addReaderMacro(c, f)

        self.addTokenSet(FLOAT_D, 'numbers')
        self.addTokenSet(INITID_D, 'identifier')

    def addToken(self, result, token):
        result.append(token)

    def parseDefault(self, c, stream, result):
        if c.isspace():
            return
        self.syntaxError("What is this crap???? %r" % c, result)

    def parseNewLine(self, c, stream, result):
        self.lineno += 1

    def parseNegative(self, c, stream, result):
        c2 = stream.read()
        if c2 in FLOAT_D:
            self.parseNumber(c2, stream, result)
            result[-1].pyvalue = -result[-1].pyvalue
        elif c2.isspace():
            stream.back()
            self.parseIdentifier(c, stream, result)
        else:
            stream.back()
            self.syntaxError("You can only put numbers after a -. Found a %r" % c2, result)

    def parseComment(self, c, stream, result):
        while c != '\n':
            c = stream.read()
        stream.back()


    def parseIdentifier(self, c, stream, result):
        id = c
        while 1:
            try:
                c = stream.read()
            except EOFError:
                break
            if c in ID_D:
                id += c
            else:
                stream.back()
                break
        self.addToken(result, O.I(id, lineno=self.lineno))

    def parseNumber(self, c, stream, result):
        num = c
        floatp = c == '.'
        while 1:
            try:
                c = stream.read()
            except EOFError:
                break
            if c and c in NUMBER_D:
                num += c
            elif c and c in FLOAT_D:
                floatp = True
                num += c
            else:
                stream.back()
                break
        if floatp:
            self.addToken(result, O.Number(float(num), lineno=self.lineno))
            return
        self.addToken(result, O.Number(int(num), lineno=self.lineno))

    escapes = {'n': '\n',
               't': '\t',
               '"': '"'}

    def parseString(self, c, stream, result):
        delim = c
        r = []
        while 1:
            try:
                c = stream.read()
            except EOFError:
                self.syntaxError("EOF in the middle of a string", result, ExpectedMore)
            if c == '\\':
                c2 = stream.read()
                if c2 in self.escapes:
                    r.append(self.escapes[c2])
            elif c == delim:
                break
            else:
                r.append(c)
        thingy = ''.join(r)
        self.addToken(result, O.String(thingy, lineno=self.lineno))



def Stream(o):
    if hasattr(o, 'seek'):
        return FileStream(o)
    elif hasattr(o, '__getitem__'):
        return ListStream(o)


class ListStream(object):
    def __init__(self, l):
        self.list = l
        self.i = -1

    def read(self):
        self.i += 1
        if len(self.list) <= self.i:
            raise EOFError("End of the list!")
        return self.list[self.i]

    def back(self):
        if self.i == -1:
            return ''
        self.i -= 1
        return self.list[self.i+1]

class FileStream(object):
    """
    s = Stream(StringIO('hello'))
    s.read() --> 'h'
    s.back() --> 'h'
    s.read() --> 'h'
    s.read() --> 'e'
    s.back() --> 'e'

    and so on.
    """
    def __init__(self, f):
        """f must be seekable"""
        self.file = f
        self.got = []
        self.getting = []

    def read(self):
        """
        Read a single character, and put it into the `got' cache.
        """
        if not self.getting:
            r = list(self.file.read())
            if not r:
                raise EOFError("EOF!")
            self.getting.extend(r)

        if self.getting:
            self.got.append(self.getting.pop(0))

        return self.got[-1]

##    def peek(self):
##        if self.getting:
##            return self.getting[0]
##        else:
##            r = list(self.file.read())
##            if not r:
##                raise EOFError("EOF!")
##            self.getting.extend(r)
##            return self.getting[0]

    def back(self):
        """
        Move back a single character in the stream. Return it.
        """
        if not self.got:
            return ''
        self.getting.insert(0, self.got[-1])
        del self.got[-1]
        return self.getting[0]

##    def peekback(self, times=1):
##        try:
##            return self.got[-1*times]
##        except IndexError:
##            return ''

