from cStringIO import StringIO
import string, operator

NUMBER_D = ''.join(map(str, range(10)))
FLOAT_D = NUMBER_D + '.'
INITID_D = string.letters + '_=+-<>/*!?'
ID_D = INITID_D + NUMBER_D + '.' #XXX dot bad

from subol import tokens as t

class ExpectedMore(SyntaxError):
    """EOF in the middle of a string/list; Expected indented block; etc"""
    pass


class AST(list):

    def __init__(self, parent):
        self.parent = parent

    def up(self):
        return self.parent

    def __repr__(self):
        return "AST[%s]" % ', '.join([repr(x) for x in self])
#def AST(ueo): return list()

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
        raise etype('at line %s, result %s: %s' % (self.lineno, result, msg))

    def addTokenSet(self, tokens, name):
        for c in tokens:
            self.tokensets[c] = name

    def addTokenType(self, type, method):
        raise NotImplementedError
        self.tokentypes[type] = method

    def parseDefault(self, c, stream, result):
        raise NotImplementedError("UEO")

    def parse(self, code):
        """
        I always return a list.
        """
        result = AST(None)
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
            result = AST(None)

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
            for type, method in self.tokentypes.items():
                if isinstance(c, type):
                    thingy = method

        # 4
        if not thingy:
            thingy = self.parseDefault

        thingy(c, stream, result)
        return result


    def addReaderMacro(self, c, fun):
        self.readtable.setdefault(c, []).append(fun)

    def removeReaderMacro(self, c, fun):
        macros = self.readtable[c]
        for i in range(len(macros), -1, -1):
            if macros[i] is fun:
                del macros[i]
                return
        raise KeyError("%s not found in %s's macro stack" % (fun, c))



class Parser(AbstractParser):
    def __init__(self):
        AbstractParser.__init__(self)

        for tok,func in [(t.OpenParen, self.parseList),
                         #(t.Bang, self.parseAddReaderMacro),
                         (t.OpenCurly, self.parseInfix),
                         (t.OpenBracket, self.parseMakeList),
                         (t.Dot, lambda *args: None),
                         #(t.Dot, self.parseDot),
                         (t.NewLine, self.parseNewLine),
                         ]:
            self.addReaderMacro(tok, func)

    def parse(self, code):
        result = AST(None)
        #import pprint
        tokens = Tokenizer().parse(code)
        #pprint.pprint(tokens)
        tokens = bracketize(tokens)
        #print "bracketize result", tokens
        assert not t.Indent in tokens
        assert not t.Dedent in tokens
        #pprint.pprint(tokens)
        s = Stream(tokens)
        while 1:
            try:
                self.read(s, result=result)
            except EOFError:
                break
        return result


    def addItem(self, result, item):
        #print "ITEM", item
        result.append(item)

    def parseDefault(self, c, stream, result):
##        if (hasattr(c, 'isspace') and c.isspace()):
##            return 
        if isinstance(c, (t.Identifier, t.Atom, t.Form)):
            self.addItem(result, c)
        elif c in (t.Colon,):
            self.syntaxError("Expected an indented block!", result, ExpectedMore)
            #self.addItem(result, c)
        elif c in (t.Indent, t.Dedent):
            pass
        else:
##            print "STREAM POSITION", stream.i
##            print "CONTEXT", stream.list[stream.i-10:stream.i+10]
##            print stream.list[stream.i-2:stream.i+2]
            self.syntaxError("Got an unexpected %r!" % c, result)



    def parseDot(self, c, stream, result):
        base = result.pop(-1)
        id = self.read(stream)
        assert len(id) == 1
        id = id[0]
        assert isinstance(id, t.Identifier), repr(id)
        result.append([t.I('attr'), base, id])

    def parseNewLine(self, c, stream, result):
        self.lineno += 1

    def parseList(self, c, stream, result, delim=t.CloseParen):
        r = AST(result)
        origi = stream.i
        origc = c
        while 1:
            try:
                c = stream.read()
            except EOFError:
                self.syntaxError("EOF in the middle of a list, expecting a %r to close the %r at pos #%s" % (delim, origc, origi), result, ExpectedMore)
            if c == delim:
                break
            self.read(stream, c, r)
        self.addItem(result, r)


    def parseMakeList(self, c, stream, result, delim=t.CloseBracket):
        self.parseList(c, stream, result, delim=delim)
        result[-1].insert(0, t.I('mklist'))


    def parseInfix(self, c, stream, result, delim=t.CloseCurly):
        self.parseList(c, stream, result, delim=delim)
        op = result[-1][1]
        del result[-1][1]
        result[-1].insert(0, op)


    def parseAddReaderMacro(self, c, stream, result):
        raise NotImplementedError("The design of this is extremely questionable")
        character = stream.read()

        # (before) Jun 14 - The Tokenizer doesn't give us whitespace
        # any more, but it's not really necessary

##        space = stream.read()
##        if space != ' ':
##            raise SyntaxError("Correct syntax is !, followed by a character to "
##                              "macro-ize, followed by a space, followed by a "
##                              "function name. You gave me !, followed by %r, "
##                              "followed by %r. YOU LOSE." % (character, space))
        id = stream.read()
        assert isinstance(id, t.Identifier), repr(id)
        f = namedObject(id.name)
        self.addReaderMacro(character, f)


class Tokenizer(AbstractParser):
    """
    I'll return a flat AST containing tokens!
    """
    def __init__(self):
        AbstractParser.__init__(self)
        self.readtable = {}
        self.indents = [] # list of numbers of indents

        plainTokens = {'[': t.OpenBracket,
                       ']': t.CloseBracket,
                       '(': t.OpenParen,
                       ')': t.CloseParen,
                       #'!': t.Bang,
                       ':': t.Colon,
                       '{': t.OpenCurly,
                       '}': t.CloseCurly,
                       }

        for c in plainTokens:
            def tokenizeSimple(c, stream, result):
                self.addToken(result, plainTokens[c])
            self.addReaderMacro(c, tokenizeSimple)

        for c, f in [('"', self.parseString),
                     ('numbers', self.parseNumber),
                     ('identifier', self.parseIdentifier),
                     ('\n', self.parseNewLine),
                     ('#', self.parseComment),
                     ('-', self.parseNegative),
                     ]:
            self.addReaderMacro(c, f)

        self.addTokenSet(FLOAT_D, 'numbers')
        self.addTokenSet(INITID_D, 'identifier')

    def addToken(self, result, token):
        #print "adding a token", repr(token)
        result.append(token)

    def parseDefault(self, c, stream, result):
        if c.isspace():
            return
        #let someone else handle it
        self.addToken(result, t.Unknown(c))


    def parseNegative(self, c, stream, result):
        c2 = stream.read()
        if c2 in FLOAT_D:
            self.parseNumber(c2, stream, result)
            result[-1] = -result[-1]
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


    def parseNewLine(self, c, stream, result):
        self.lineno += 1
        spaces = 0
        indentLevel = 0
        if self.indents:
            indentLevel = reduce(operator.add, self.indents)
        while 1:
            try:
                c = stream.read()
            except EOFError:
                break
            if c == ' ':
                spaces += 1
            elif c == '\n':
                stream.back()
                self.addToken(result, t.NewLine)
                return

            # Jesus this code is horrible - it's very precariously crafted so the number of NewLines is correct 
            
            elif c == '#':
                while c != '\n':
                    c = stream.read()
                self.addToken(result, t.NewLine)
                stream.back() # We want to still process the next newline
                return
            else:
                stream.back()
                break

        #self.spaces = spaces
        if spaces > indentLevel:
            self.addToken(result, t.Indent)
            self.indents.append(spaces - indentLevel)
        elif spaces < indentLevel:
            #how many dedents?
            ## indented twice, once with 3 and once with 7 spaces
            ## back to the beginning; spaces = 0.
            dedents = 0
            crap = spaces
            while crap != indentLevel:
                dedents += 1
                crap += self.indents.pop()
                if crap > indentLevel:
                    raise RuntimeError("WTF %s is > than %s on line %s" % (crap, indentLevel, self.lineno))
            for dedent in range(dedents):
                self.addToken(result, t.Dedent)

        self.addToken(result, t.NewLine)

        #self.indentLevel = spaces

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
        self.addToken(result, t.I(id))

    def parseNumber(self, c, stream, result):
        num = c
        floatp = c == '.'
        if floatp and stream.peek() not in FLOAT_D:
            self.addToken(result, t.Dot)
            return
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
            self.addToken(result, float(num))
            return
        try:
            self.addToken(result, int(num))
        except ValueError:
            self.addToken(result, long(num))

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

                # XXX I don't remember why I put this here. Apparently
                # I was assuming that I might continue reading on
                # after the end delimiter was found... Removing it
                # didn't break any tests, though, and fixed a new one
                # (testStrings with '"')
##                if stream.peekback() == delim and stream.peekback(2) != '\\':
##                    print "WTF", repr(stream.peekback()), repr(stream.peekback(2))
##                    break
##                else:
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
        self.addToken(result, thingy)



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

    def peek(self):
        try:
            return self.list[self.i+1]
        except IndexError:
            raise EOFError("HRR")

    def peekback(self):
        try:
            return self.list[self.i-1]
        except IndexError:
            raise EOFError("Beginning of the list for peekback")

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

    def peek(self):
        if self.getting:
            return self.getting[0]
        else:
            r = list(self.file.read())
            if not r:
                raise EOFError("EOF!")
            self.getting.extend(r)
            return self.getting[0]

    def back(self):
        """
        Move back a single character in the stream. Return it.
        """
        if not self.got:
            return ''
        self.getting.insert(0, self.got[-1])
        del self.got[-1]
        return self.getting[0]

    def peekback(self, times=1):
        try:
            return self.got[-1*times]
        except IndexError:
            return ''

# utilities

class NoTokenFound(Exception):
    pass

def searchBackwards(l, start, find, ignore=NotImplemented):
    i = start
    while 1:
        if i < 0:
            raise NoTokenFound("Sorry!")
        thing = l[i]
        if ignore is NotImplemented and thing is find:
            return i
        elif (ignore is not NotImplemented) and (thing is not ignore):
            if thing is find:
                return i
            else:
                raise ValueError("Expected %s, got %s" % (find, thing))
        i -= 1

class NoCloserFound(Exception):
    pass

def findMatchingTokens(tokens, opener, closer, start=0):
    openers = 1
    i = start
    while 1:
        if len(tokens) <= i:
            raise NoCloserFound("Couldn't find %s" % closer)
        if tokens[i] is t.Indent:
            openers += 1
        if tokens[i] is t.Dedent:
            openers -= 1
            if not openers:
                return i
        i += 1

## rundown. Find an Indent. Ensure that immediately preceding it
## (except for NewLines) is a Colon. Delete the Indent. Delete the
## Colon. Traverse backwards until another NewLine is found. Replace
## it with an opener. Now go on from there until you find a
## matching Dedent. (If no Dedent is found, put a closer at the
## very end of the token stream.)

# this breaks if there's an indentation not preceded by a colon.... So
# in that case, we need to DELETE the Indentation, DELETE its
# associated Dedent, and RETURN.



def _bracketize(tokens, opener=t.OpenParen, closer=t.CloseParen):
    origi = tokens.index(t.Indent)
    if origi != 0:
        i = origi - 1
    else:
        i = origi
    assert i >= 0, tokens
    try:
        colonI = searchBackwards(tokens, i, t.Colon, ignore=t.NewLine)
        assert colonI >= 0, "2"
    except (ValueError, NoTokenFound):
        #There is no Colon!! Clean up crew beep beep coming through
        del tokens[origi]
        try:
            i = findMatchingTokens(tokens, t.Indent, t.Dedent, origi)
            assert tokens[i] is t.Dedent, "GRR"
            assert i >= 0, "ONO"
            del tokens[i]
        except NoCloserFound:
            #print "???"
            pass
        return tokens
        

    del tokens[colonI] # del colon
    assert tokens[origi-1] is t.Indent
    del tokens[origi-1] # del indent

    # Start looking backwards for a NewLine from the point that we found the Colon.
    # sub 1 because we've deleted the colon
    i = colonI - 1 

    assert i >= 0, "3"

    try:
        i = searchBackwards(tokens, i, t.NewLine)
        assert i >= 0, "4"
    except NoTokenFound:
        tokens.insert(0, opener)

    #print "found NewLine!", tokens[i], i, "inserting opener after it"
    tokens.insert(i+1, opener)

    try:
        i = findMatchingTokens(tokens, t.Indent, t.Dedent, i)
        assert i >= 0, "5"
        tokens[i] = closer
    except NoCloserFound:
        tokens.append(closer)


    return tokens

def bracketize(tokens, opener=t.OpenParen, closer=t.CloseParen):
    tokens = tokens[:]
    while t.Indent in tokens:
        tokens = _bracketize(tokens, opener, closer)
    #tokens =  [x for x in tokens if x is not t.NewLine]
    return tokens


def namedModule(name):
    """Return a module given its name."""
    topLevel = __import__(name)
    packages = name.split(".")[1:]
    m = topLevel
    for p in packages:
        m = getattr(m, p)
    return m


def namedObject(name):
    """Get a fully named module-global object.
    """
    classSplit = string.split(name, '.')
    module = namedModule(string.join(classSplit[:-1], '.'))
    return getattr(module, classSplit[-1])

def splitseq(seq, delim):
    l = []
    while 1:
        try:
            i = seq.index(delim)
        except ValueError:
            if seq:
                l.append(seq)
            break
        l.append(seq[:i])
        seq = seq[i+1:]
    return l
