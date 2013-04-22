from subol import parse
from subol.tokens import I

from twisted.trial import unittest

import cStringIO, sys

class Stream(unittest.TestCase):
    def testStream(self):
        f = cStringIO.StringIO('hello')
        s = parse.Stream(f)
        d =[(s.read, 'h'),
            (s.back, 'h'),
            (s.back, ''),
            (s.read, 'h'),
            (s.read, 'e'),
            (s.back, 'e'),
            (s.read, 'e'),
            (s.read, 'l'),
            (s.read, 'l'),
            (s.read, 'o'),
            (s.back, 'o'),
            (s.read, 'o')]

        for f, res in d:
            self.assertEquals(f(), res)
        self.assertRaises(EOFError, s.read)

    def testListStream(self):
        f = list('hello')
        s = parse.Stream(f)
        d =[(s.read, 'h'),
            (s.back, 'h'),
            (s.back, ''),
            (s.read, 'h'),
            (s.read, 'e'),
            (s.back, 'e'),
            (s.read, 'e'),
            (s.read, 'l'),
            (s.read, 'l'),
            (s.read, 'o'),
            (s.back, 'o'),
            (s.read, 'o')]

        for f, res in d:
            v = f()
            self.assertEquals(v, res)
        self.assertRaises(EOFError, s.read)


class Parse(unittest.TestCase):
    def setUp(self):
        self.p = parse.Parser()

    def testSimple(self):
        p = self.p.parse
        self.assertEquals(p('10'), [10])
        self.assertEquals(p('10.0'), [10.0])
        self.assertEquals(p('.1'), [0.1])
        bignum = sys.maxint + 1
        self.assertEquals(p(str(bignum)), [bignum])

    def testMinus(self):
        p = self.p.parse
        self.assertEquals(p('-1'), [-1])
        self.assertEquals(p('(- 1 2)'), [[I('-'), 1, 2]])

    def testStrings(self):
        p = self.p.parse
        self.assertEquals(p('"argh"'), ['argh'])
        self.assertEquals(p('"hello\\" there\\""'), ['hello" there"'])
        self.assertRaises(SyntaxError, p, '"hel')
        self.assertRaises(SyntaxError, p, '"')

    def testLists(self):
        p = self.p.parse
        self.assertEquals(p('(1 2 3)'), [[1, 2, 3]])
        self.assertEquals(p('(1 2 "3")'), [[1, 2, '3']])
        self.assertEquals(p('(1 (2) "3")'), [[1, [2], '3']])
        self.assertRaises(SyntaxError, p, '(1 2 ')

    def testIdentifiers(self):
        p = self.p.parse
        self.assertEquals(p('a'), [I('a')])

    def testFunkyLists(self):
        p = self.p.parse
        c = '''
        (foo bar) (baz quux)
        '''

        self.assertEquals(p(c), [[I('foo'), I('bar')],
                                 [I('baz'), I('quux')]])

    def testIndentation(self):
        p = self.p.parse
        c = '''
        foo:
            bar
        '''
        self.assertEquals(p(c), [[I('foo'), I('bar')]])

    def testHardcoreIndentation(self):
        p = self.p.parse
        c = '''
        class foo:
            def bar (self):
                print "hello!!!"
            '''
        self.assertEquals(p(c), [[I('class'), I('foo'), [I('def'), I('bar'), [I('self')], I('print'), "hello!!!"]]])

    def testReallyHardcoreIndentation(self):
        p = self.p.parse
        # The whitespace in the following string is very important
        c = '''
foo:
    bar
        
    baz:
        quux

        hooj

    hello

'''
        v = p(c)
        self.assertEquals(v, [[I('foo'),
                               I('bar'),
                               [I('baz'), I('quux'), I('hooj')],
                               I('hello'),
                               ]])

    def testDoubleDedentIndentation(self):
        p = self.p.parse
        c = '''
foo:
    bar:
        baz:
            wtf
quux'''
        self.assertEquals(p(c),
                          [[I('foo'), [I('bar'), [I('baz'), I('wtf')]]], I('quux')]
                          )

    def testDoubleDedentNoNotReally(self):
        p = self.p.parse
        c = '''
(foo (bar (baz wtf)))
quux'''
        self.assertEquals(p(c),
                          [[I('foo'), [I('bar'), [I('baz'), I('wtf')]]], I('quux')])

    def testBadIndentation(self):
        p = self.p.parse
        c = '''
def foo:
bar'''
        self.assertRaises(SyntaxError, p, c)
        
    def testAddMacro(self):
        raise unittest.SkipTest("reader-macro-adder is disabled for now")
        global macrotest
        l = []
        def macrotest(c, *args):
            l.append(c)
        p = self.p.parse

        # XXX - we want Tokenizer to return Unknowns, and they need to
        # be handled properly by the Parser when they're found --
        # OR.... put the reader macros on the Tokenizer

        c = '''
        !$ subol.test.test_parser.macrotest
        $$$
        '''
        p(c)
        self.assertEquals(len(l), 3)
        self.assertEquals(l, ['$']*3)


    def testComment(self):
        p = self.p.parse
        c = '''(1 2 #three)
                4 5)'''

        self.assertEquals(p(c), [[1, 2, 4, 5]])

from subol import tokens as t

class Tokenize(unittest.TestCase):
    def setUp(self):
        self.p = parse.Tokenizer()

    def testSimple(self):
        p = self.p.parse
        c = '''\
[1 2 3] "foo" 31.12
 (1)
'''
        r = p(c)
        e = [t.OpenBracket, 1, 2, 3, t.CloseBracket,
             "foo", 31.12, t.Indent, t.NewLine, t.OpenParen, 1, t.CloseParen, t.Dedent, t.NewLine]
        self.assertEquals(r, e)


    def testDoubleDedent(self):
        p = self.p.parse
        c = '''
foo:
    bar:
        baz:
            wtf
quux'''
        v = p(c)
        e = [t.NewLine, I('foo'), t.Colon, t.Indent, t.NewLine, I('bar'),
             t.Colon, t.Indent, t.NewLine, I('baz'), t.Colon, 
             t.Indent, t.NewLine, I('wtf'), 
             t.Dedent, t.Dedent, t.Dedent, t.NewLine, I('quux')]
        self.assertEquals(v, e)

    def testBracketize(self):
        ob = t.OpenBracket
        cb = t.CloseBracket

        op = t.OpenParen
        cp = t.CloseParen
        
        tokens = [t.NewLine, t.I('def'), t.I('foo'), op, cp, t.Colon,
                  t.NewLine, t.Indent, op, t.I('bar'), cp,
                  t.NewLine, t.I('def'), t.I('baz'), op, cp, t.Colon,
                  t.NewLine, t.Indent, t.I('quux'),
                  t.NewLine, t.Dedent, t.Dedent, t.I('hooj'),
                  t.NewLine]

        expected = [op, t.I('def'), t.I('foo'), op, cp,
                    op, t.I('bar'), cp,
                    op, t.I('def'), t.I('baz'), op, cp,
                    t.I('quux'),
                    cp, cp, t.I('hooj')]

        result = parse.bracketize(tokens)
        result = [x for x in result if x is not t.NewLine]

        self.assertEquals(result, expected)


    def testCrappyBracketize(self):
        p = self.p.parse
        c = '''
class Subol (unittest.TestCase):

    def testMath (self):
        (self.assertEquals (+ 3 (/ 6 2)) 6)
        (self.assertEquals (- 3 2) 1)
        (self.assertEquals (* 5 5) 25)

    def testInfix (self):
        (self.assertEquals {3 + {6 / 2}} 6)
        {a = 1}
        (= b 2)
        (self.assertEquals a 1)
        (self.assertEquals b 2)
        '''

        ob = t.OpenBracket
        cb = t.CloseBracket

        op = t.OpenParen
        cp = t.CloseParen

        oc = t.OpenCurly
        cc = t.CloseCurly
        
        expected = [op, t.I('class'), t.I('Subol'), op, t.I('unittest.TestCase'), cp,
                    op, t.I('def'), t.I('testMath'), op, t.I('self'), cp,
                    op, t.I('self.assertEquals'), op, t.I('+'), 3, op, t.I('/'), 6, 2, cp, cp, 6, cp,
                    op, t.I('self.assertEquals'), op, t.I('-'), 3, 2, cp, 1, cp,
                    op, t.I('self.assertEquals'), op, t.I('*'), 5, 5, cp, 25, cp,
                    cp, #close testMath

                    op, t.I('def'), t.I('testInfix'), op, t.I('self'), cp,
                    op, t.I('self.assertEquals'), oc, 3, t.I('+'), oc, 6, t.I('/'), 2, cc, cc, 6, cp,
                    oc, t.I('a'), t.I('='), 1, cc,
                    op, t.I('='), t.I('b'), 2, cp,
                    op, t.I('self.assertEquals'), t.I('a'), 1, cp,
                    op, t.I('self.assertEquals'), t.I('b'), 2, cp,
                    cp, #close testInfix
                    cp, #close class
                    ]
        v = p(c)
        v2 = parse.bracketize(v)
        result = [x for x in v2 if x is not t.NewLine]
##        for a, b in zip(v2, expected, ):
##            print "---"
##            print a, b
##            print "==="
        self.assertEquals(result, expected)


