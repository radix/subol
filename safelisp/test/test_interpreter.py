import sys

from twisted.trial import unittest

from safelisp import interpreter
from safelisp import builtins
from safelisp import objects as O
from safelisp import environment as E


def testHandler(interp):
    raise
builtins.builtins['*exc-handler*'] = testHandler

def es(*args, **kwargs):
    return O.simplify(interpreter.evalString(*args, **kwargs))



class FunctionTest(unittest.TestCase):

    def testSavedLambda(self):
        self.assertEquals(
            es('(def FOOM (lambda () 5)) (FOOM)'),
            5)


    def testDefun(self):
        self.assertEquals(
            es('(defun (doIt) 3) (doIt)'),
            3)


    def testSimpleLambda(self):
        self.assertEquals(
            es('((lambda (x) 4) 1)'),
            4)


    def testLessSimpleLambda(self):
        self.assertEquals(
            es('((lambda (x y z) (+ x y z)) 1 2 3)'),
            6)


    def testAmpersandArgs(self):
        self.assertEquals(
            es('((lambda (&y) y) 1 2 3)'),
            [1, 2, 3])


    def testSomeAmpersandArgs(self):
        self.assertEquals(
            es('((lambda (x &y) y) 1 2 3)'),
            [2, 3])

    
    def testAmpersandArgsBeforeRegularArgFails(self):
        self.assertRaises(
            O.ParameterError,
            es, '(set *exc-handler* None) (lambda (&x y) 1 2 3)')


    def testTooManyArgs(self):
        self.assertRaises(
            O.ApplicationError,
            es, '((lambda (x) ha) 2 4)')


    def testNotEnoughArgs(self):
        self.assertRaises(
            O.ApplicationError,
            es, '((lambda (x) hoo))')



class EvaluatorTest(unittest.TestCase):

    def testSimpleLiterals(self):
        self.assertEquals(es('"hello :o)"'), 'hello :o)')
        self.assertEquals(es('3.14'), 3.14)


    def testVariables(self):
        self.assertEquals(
            es("(def this-should-not-exist 1) this-should-not-exist"),
            1)


    def testAddition(self):
        self.assertEquals(
            es('(+ 4 5 6)'),
            15)


    def testEqualsAndAddition(self):
        self.assertEquals(
            es('(== 3 (+ 2 1))'),
            True)


    def testSlicing(self):
        self.assertEquals(
            es('(slice [1 2 3] 1 2)'),
            [2])


    def testSlicingToEnd(self):
        self.assertEquals(
            es('(slice [1 2 3] 1 None)'),
            [2, 3])


    def testSlicingFromBeginning(self):
        self.assertEquals(
            es('(slice [1 2 3] 0 1)'),
            [1])


    def testCar(self):
        self.assertEquals(
            es('(car [1 2 3])'), 1)


    def testCdr(self):
        self.assertEquals(
            es('(cdr [1 2 3])'), [2, 3])


    def testDictConstruction(self):
        self.assertEquals(
            es('(dict 1 2 3 4)'),
            {1: 2, 3: 4})


    def testDictLookupNumber(self):
        self.assertEquals(
            es('(index (dict 1 2 3 4) 1)'),
            2)


    def testDictLookupString(self):
        self.assertEquals(
            es('(index (dict "hi" "there" "hoo" "hee") "hoo")'),
            "hee")


    def testPrint(self):
        from cStringIO import StringIO
        io = StringIO()
        old = sys.stdout
        try:
            sys.stdout = io
            es('(println "hi" "there")')
            es('(print "shmuck")')
            es('(println ["oo" "on" "you"])')
        finally:
            sys.stdout = old

        self.assertEquals(io.getvalue(), 
                          "hi there\nshmuck['oo', 'on', 'you']\n")


    def testExcHandler(self):
        env = interpreter.defaultEnvironment()
        es('(defun (my-exc-handler exc message frames) (l:append exc))', env)
        es('(def l [])', env)
        es('(set *exc-handler* my-exc-handler)', env)
        es('(/ 1 0)', env)
        self.assertEquals(es('l', env), ["ZeroDivisionError"])


    def testMacros(self):
        self.assertEquals(
            es('(defmacro (mymac arg arg2) 3) (mymac 4 5)'),
            3)

        self.assertEquals(
            es('(defmacro (mymac arg &rest) (+ [(I +)] rest)) (mymac 1 2 3)'),
            5)


    def testQuote(self):
        self.assertEquals(
            es('(I foo)'),
            O.I('foo'))

        self.assertEquals(
            es('(I (foo bar))'),
            [O.I('foo'), O.I('bar')])


    def testStack(self):
        interp = interpreter.defaultInterpreter()
        env = interpreter.defaultEnvironment()

        errors = []

        def handle(interp):
            framenames = [x.name for x in interp.frames]
            errors.append(O.simplify(framenames))
            raise

        #First, let's muck up the stack:
        E.set(env, '*exc-handler*', None)
        self.assertRaises(ZeroDivisionError,
                          interp.evalString,
                          '''
                          (defun (ham) (eggs))
                          (defun (eggs) (/ 1 0))
                          (ham)
                          ''',
                          env)

        # Now, let's see if it was cleaned properly (and that our
        # handler can work):
        E.set(env, '*exc-handler*', handle)

        self.assertRaises(ZeroDivisionError,
                          interp.evalString,
                          '''
                          (defun (foo) (bar))
                          (defun (bar) (/ 1 0))
                          (foo)
                          ''',
                          env)
        self.assertEquals(errors, [['foo', 'bar']])


    def testMaxInstructions(self):
        env = interpreter.defaultEnvironment()

        es('(+ 1 2)', env, maxInstructions=4)

        E.set(env, '*exc-handler*', None)
        self.assertRaises(interpreter.TooManyInstructions,
                          es, '(+ 1 2 3)', env, maxInstructions=4)



    def testAttributeError(self):
        self.assertRaises(AttributeError, es, '(getattr 1 "hi")')


    def testSetGet(self):
        # Setting attributes on numbers might not work forever :-)
        self.assertEquals(
            es('''(def x 1)
            (setattr x "hi" 2)
            (getattr x "hi")'''),
            2)


    def testAttributeSyntaxAttributeError(self):
        self.assertRaises(AttributeError, es, '(1:hi)')


    def testAttributeSyntaxGetattr(self):
        self.assertEquals(
            es('''(def x 1)
            (setattr x "hi" 2)
            x:hi'''),
            2)


    def testSetattrSyntax(self):
       self.assertEquals(
           es('''(def x 1)
           (set x:hi 2)
           (x:hi)'''),
           2)
    testSetattrSyntax.skip = "Implement setattr syntax"


    def testFor(self):
        self.assertEquals(
            es('(for x [1 2 3] 9 (+ x 2))'),
            [3,4,5])


    def testLet(self):
        self.assertEquals(
            es('(let ((x 1) (y 2)) (+ x y))'),
            3)



class ObjectTest(unittest.TestCase):
    def testObjects(self):
        self.assertEquals(
            es('(def o (make-class "foo" [] (defun (meth) 3))) (o:meth)'),
            3)
