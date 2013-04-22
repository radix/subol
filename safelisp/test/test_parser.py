from safelisp import parse
from safelisp import objects as O

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
        p = parse.Parser()
        self.p = lambda x: O.simplify(p.parse(x))

    def testCrap(self):
        p = self.p
        self.assertRaises(SyntaxError, p, '^')
        self.assertRaises(parse.ExpectedMore, p, '(')

    def testNumbers(self):
        p = self.p
        self.assertEquals(p('10'), [10])
        self.assertEquals(p('10.0'), [10.0])
        self.assertEquals(p('.1'), [0.1])
        bignum = sys.maxint + 1
        self.assertEquals(p(str(bignum)), [bignum])

        self.assertRaises(SyntaxError, p, '-x')

    def testMinus(self):
        p = self.p
        self.assertEquals(p('-1'), [-1])
        self.assertEquals(p('(- 1 2)'), [[O.I('-'), 1, 2]])

    def testStrings(self):
        p = self.p
        self.assertEquals(p('"argh"'), ['argh'])
        self.assertEquals(p('"hello\\" there\\""'), ['hello" there"'])
        self.assertRaises(SyntaxError, p, '"hel')
        self.assertRaises(SyntaxError, p, '"')

    def testLists(self):
        p = self.p
        self.assertEquals(p('(1 2 3)'), [[1, 2, 3]])
        self.assertEquals(p('(1 2 "3")'), [[1, 2, '3']])
        self.assertEquals(p('(1 (2) "3")'), [[1, [2], '3']])
        self.assertRaises(parse.ExpectedMore, p, '(1 2 ')

    def testIdentifiers(self):
        p = self.p
        self.assertEquals(p('a'), [O.I('a')])

    def testFunkyLists(self):
        p = self.p
        c = '''
        (foo bar) (baz quux)
        '''

        self.assertEquals(p(c), [[O.I('foo'), O.I('bar')],
                                 [O.I('baz'), O.I('quux')]])

    def testComment(self):
        p = self.p
        c = '''(1 2 #three)
                4 5)'''

        self.assertEquals(p(c), [[1, 2, 4, 5]])

    def testMakeList(self):
        p = self.p
        self.assertEquals(p('[1 2]'), [[O.I('vec'), 1, 2]])

    def testGetattr(self):
        p = self.p
        self.assertEquals(p('1:hoo'), [[O.I('getattr'), 1, 'hoo']])



class Tokenize(unittest.TestCase):
    def setUp(self):
        p = parse.Tokenizer()
        self.p = lambda x: O.simplify(p.parse(x))

    def testSimple(self):
        p = self.p
        c = '''\
[1 2 3] "foo" 31.12
 (1)
'''
        r = p(c)
        e = [O.OpenBracket(0), 1, 2, 3, O.CloseBracket(0),
             "foo", 31.12, O.OpenParen(0), 1, O.CloseParen(0)]
        self.assertEquals(r, e)

