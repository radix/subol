"""
A lame Subol-to-Python-bytecode compiler; I just generate Python ASTs
and generate the bytecode from them.

TODO: In the future, I'll need to generate Python bytecodes directly
if I want any kind of neat features. (TCO, lexical scoping, etc.)
"""

import os, sys


from subol.tokens import I, Identifier, Atom, Form, NewLine
from subol.parse import Parser

from compiler import pycodegen, misc, syntax, ast, consts

# a horrible horrible hack :(
class Ignore: pass



class Compiler(object):
    """
    This class isn't strictly necessary, I just wanted to use
    getattr(self, name) rather than globals(name) :P
    """

    def __init__(self):
        comparisons = {'eq' : '==',
                       '==' : '==',
                       'is' : 'is',
                       'lt' : '<',
                       '<'  : '<',
                       'gt' : '>',
                       '>'  : '>',
                       'gte': '>=',
                       '>=' : '>=',
                       'lte': '<=',
                       '<=' : '<=',
                       'ne' : '!=',
                       '!=' : '!=',
                       }

        self.macros = {}

        self.specials = {'=': self.special_set,
                         }

        for k,v in comparisons.items():
            def c(form, comparison=v):
                first = self.reallyCompile(form[1])
                second = self.reallyCompile(form[2])
                return ast.Compare(first,
                                   [(comparison, second)])

            self.specials[k] = c

        math = {'/': 'div',
                '*': 'mul',
                '+': 'add',
                '-': 'sub',
                }
        for op, name in math.items():
            opk = getattr(ast, name.capitalize())
            def mathItUp(form, opk=opk):
                return reduce(lambda x, y: opk((x, y)),
                              map(self.reallyCompile, form[1:]))

            self.specials[op] = mathItUp
            self.specials[name] = mathItUp

    def compileModule(self, code):
        """
        Return a Python AST.
        """
        r = ast.Module(None, self.compileSuite(code))
        #print r
        return r

    def compileSuite(self, code, discard=False):
        out = self.compileForms(code)
        if discard:
            out = map(ast.Discard, out)
        return ast.Stmt(out)

    def compileForms(self, forms):
        return [self.reallyCompile(form) for form in forms]

    def compileExpr(self, code):
        return ast.Expression(self.reallyCompile(code))


    def getCode(self, ast, mode='single', filename='<Subol>'):
        #print "ast is", ast
        misc.set_filename(filename, ast)
        # worklist = [ast]
        # while worklist:
        #     node = worklist.pop(0)
        #     node.filename = filename
        #     worklist.extend(node.getChildNodes())
        #     print "NODE CHILDREN ARE", node, worklist

        syntax.check(ast)
        d = {'single': pycodegen.InteractiveCodeGenerator,
             'exec': pycodegen.ModuleCodeGenerator,
             'eval': pycodegen.ExpressionCodeGenerator}
        try:
            gen = d[mode](ast)
            gen.graph.setFlag(consts.CO_GENERATOR_ALLOWED)
            code = gen.getCode()
            return code
        except:
            print "THERE WAS AN ERROR DURING COMPILATION."
            print "The ast with the problem was"
            print
            print ast
            print
            print "A diagnostic traceback follows."
            raise

    def reallyCompile(self, form):

        if isinstance(form, Identifier):
            #os.path.isdir --> Gettattr(Gettattr(Name('os'), 'path'), 'isdir')
            l = form.name.split('.')
            r = ast.Name(l[0])
            for el in l[1:]:
                r = ast.Getattr(r, el)
            return r

        if isinstance(form, Atom):
            return ast.Const(form)

        if isinstance(form, NewLine):
            return

        if not isinstance(form, Form):
            raise SyntaxError("wtf is this shit, %r, %s" % (form, type(form)))

        if not len(form):
            return ast.Name('None')

        #horrible, horrible hack
        if form[0] is Ignore:
            return
        
        if isinstance(form[0], Identifier):
            sname = 'special_' + form[0].name
            if hasattr(self, sname):
                g = getattr(self, 'special_' + form[0].name)(form)
                return g
            
            if self.specials.has_key(form[0].name):
                return self.specials[form[0].name](form)
        
            if self.macros.has_key(form[0].name):
                return self.applyMacro(form)

        #assert isinstance(form[0], Identifier)
        return self.funcall(form)


    def funcall(self, form):
        realargs = list(form[1:])
        restarg = kwrestarg = None
        kwi = resti = None

        for i in range(len(realargs)):
            arg = realargs[i]
            if isinstance(arg, I) and arg.name.startswith('**'):
                kwrestarg = ast.Name(arg.name[2:])
                del realargs[i]
                break

        
        for i in range(len(realargs)):

            arg = realargs[i]
            if isinstance(arg, I) and arg.name.startswith('*'):
                restarg = ast.Name(arg.name[1:])
                del realargs[i]
                break


        realargs = self.compileForms(realargs)
        r = ast.CallFunc(self.reallyCompile(form[0]),
                            realargs, restarg, kwrestarg)
        return r


    ## Special Forms ##

    def special_import(self, form):
        """
        [import name grab ...]
        Import `name'. If any `grab's are indicated, import them as
        `name.grab' and bind `grab' to the imported object in the
        local namespace.
        """
        if len(form) == 2:
            return ast.Import([(form[1].name, None)])
        else:
            r = ast.From(form[1].name, [(x.name, None) for x in form[2:]], -1)
            return r



    def special_set(self, form):
        """
        [set name value]
        """
        val = self.reallyCompile(form[2])

        if isinstance(form[1], Form):
            assignment = [ast.AssTuple([self._assignify(x.name) for x in form[1]])]
        elif isinstance(form[1], Identifier):
            assignment = [self._assignify(form[1].name)]
        else:
            print "uh", repr(form[1])
        return ast.Assign(assignment, val)



    def _assignify(self, name):
        if '.' in name:
            splitted = name.split('.')
            basename = '.'.join(splitted[:-1])
            ga = self.reallyCompile(I(basename)) # should be either a Getattr or a Name
            return ast.AssAttr(ga, splitted[-1], 'OP_ASSIGN')
        return ast.AssName(name, 'OP_ASSIGN')

    def special_attr(self, form):
        if not len(form) == 3:
            raise SyntaxError("attr requires exactly two arguments")
        if not isinstance(form[2], Identifier):
            raise SyntaxError("Second argument to attr must be an identifier")
        return ast.Getattr(self.reallyCompile(form[1]), form[2].name)


    def special_class(self, form):
        """
        [class name (bases) (doc) suite]
        """
        if not len(form) >= 3:
            raise SyntaxError("Not enough forms")
        bases = form[2]
        doc, code = self._getDocAndCode(form[3:])
        return ast.Class(form[1].name, self.compileForms(bases), doc, code)


    def _getMagicCodeForArgs(self, args):
        magicode = 0

        for i in range(len(args)):
            arg = args[i]
            if arg.startswith('**'):
                args[i] = arg[2:]
                magicode += 8

        for i in range(len(args)):
            arg = args[i]
            if arg.startswith('*'):
                args[i] = arg[1:]
                magicode += 4

        return magicode
        
    def special_def(self, form):
        """
        [def [name arglist] (doc) suite]
        """
        if not len(form) >= 3:
            raise SyntaxError("Not enough forms in %s" % form)
        if not isinstance(form[1], Form):
            raise SyntaxError("Expected a list of [funname args...]")

        doc, code = self._getDocAndCode(form[2:])
        #print "GOT", code
        #code.nodes[-1] = ast.Return(code.nodes[-1])
        args = [x.name for x in form[1][1:]]
    
        magicode = self._getMagicCodeForArgs(args)
        
        return ast.Function(None, form[1][0].name, args, [], magicode, doc, code)

    def special_return(self, form):
        if not 1 < len(form) < 3:
            raise SyntaxError("Need exactly one argument")
        return ast.Return(self.reallyCompile(form[1]))

    def special_not(self, form):
        if not 1 < len(form) < 3:
            raise SyntaxError("Need exactly one argument")
        return ast.Not(self.reallyCompile(form[1]))

    def _getDocAndCode(self, crud):
        doc = isinstance(crud[0], str) and crud[0] or None
        if doc:
            code = crud[1:]
        else:
            code = crud
        return doc, self.compileSuite(code)

##    def special_print(self, forms):
##        """
##        [print obj ...]
##        """
##        return ast.Stmt([ast.Printnl(self.compileForms(forms[1:]), None)])

    def special_slice(self, form):
        """
        [slice obj i]
        [slice obj start end]
        [slice obj start end step]
        """
        obj = self.reallyCompile(form[1])
        rest = form[2:]
        if len(rest) == 1:
            return ast.Subscript(obj, 'OP_APPLY', [self.reallyCompile(rest[0])])
        elif len(rest) == 2:
            return ast.Slice(obj, 'OP_APPLY', *self.compileForms(rest))
        elif len(rest) == 3:
            return ast.Subscript(obj, 'OP_APPLY', [ast.Sliceobj(self.compileForms(rest))])
        else:
            raise SyntaxError("Too many thingies to slice! %r" % rest)

    def special_defmacro(self, form):
        """
        [defmacro [name args...] suite] #XXX doc
        """
        if not len(form) >= 3:
            raise SyntaxError("Not enough forms")
        #print form
        form[0] = I('def')
        #print "Macro s-exps:", form
        fun = self.compileModule([form])
        #print "macro-function:", fun
        code = self.getCode(fun, mode='exec')
        ns = makeNS({})
        #print "EVALING", code, "IN", ns
        eval(code, ns)
        self.macros[form[1][0].name] = ns[form[1][0].name]
        #print "GOT THE MACRO!", ns[form[1].name]

    def applyMacro(self, form):
        macro = self.macros[form[0].name]
        o = macro(*[x for x in form[1:]])
        #print "Macro output:", o
        if not o:
            return
        c = self.reallyCompile(o)
        #print "Compiled...", c
        return c
    
    def special_quote(self, form):
        return [hasattr(x, 'name') and x.name or x for x in form[1:]]

    def special_mklist(self, form):
        return ast.List(self.compileForms(form[1:]))

    def special_if(self, form):
        """
        [if cond form]
        ([else form])
        """
        testforms = [form[1:]]
        elseform = None

        startIndex = None

        parent = form.up()

        for i in range(len(parent)):
            x = parent[i]
            if x is form:
                startIndex = i

        if startIndex is None:
            raise RuntimeError("Bad")

        # find following forms that begin with `elif' and `else'. We
        # break on anything else. Accumulate number of forms to delete.
        index = startIndex + 1

        while index < len(parent):
            f = parent[index]
            if isinstance(f, Form) and len(f) and isinstance(f[0], Identifier):
                if f[0].name == 'elif':
                    testforms.append(f[1:])
                    f.insert(0, Ignore)
                elif f[0].name == 'else':
                    elseform = f[1:]
                    f.insert(0, Ignore)
                    # there should be nothing after else
                    break 
                else:
                    # Anything other than elif or else, break
                    break 
            else:
                # it doesn't look anything at all like an else or an elif form
                break 
            index += 1

        tests = [(self.reallyCompile(t[0]), self.compileSuite(t[1:])) for t in testforms]
        else_ = elseform and self.compileSuite(elseform)

        r = ast.If(tests, else_)
        return r

    def special_raise(self, form):
        if not 1 < len(form) < 3:
            raise SyntaxError("Need exactly a single argument")
        return ast.Raise(self.reallyCompile(form[1]), None, None)

    def special_while(self, form):
        test = form[1]
        body = form[2:]
        r = ast.While(self.reallyCompile(test), self.compileSuite(body), None)
        return r

    def special_for(self, form):
        if isinstance(form[1], Identifier):
            assign = ast.AssName(form[1].name, 'OP_ASSIGN')
        elif isinstance(form[1], Form):
            assign = ast.AssTuple([ast.AssName(x.name, 'OP_ASSIGN') for x in form[1]])
        else:
            raise SyntaxError("first argument must be an Identifier.")

        it = self.reallyCompile(form[2])

        # YOW, man, this is crazy. If I don't wrap ast.Discards around
        # each statement, for some reason I get a "NoneType object is
        # not iterable" before the second iteration of any for loop. I
        # *guess* this means that it's using the result of the last
        # expression as the iterable!?!? or some crap.
        
        suite = self.compileSuite(form[3:], discard=True)
        r = ast.For(assign, it, suite, None)
        return r

    def special_break(self, form):
        if not len(form) == 1:
            raise SyntaxError("break takes no args")
        return ast.Break()

    def special_yield(self, form):
        if not len(form) == 2:
            raise SyntaxError("yield takes one arg")
        return ast.Yield(self.reallyCompile(form[1]))

    def special_setitem(self, form):
        """
        setitem obj key value
        """
        obj = self.reallyCompile(form[1])
        key = self.reallyCompile(form[2])
        value = self.reallyCompile(form[3])
        return ast.Assign([ast.Subscript(obj,
                                         'OP_ASSIGN',
                                         [key])],
                           value)

    def special_lambda(self, form):
        if not len(form) >= 3:
            raise SyntaxError("Not enough forms in %s" % form)
        if not isinstance(form[1], Form):
            raise SyntaxError("Expected a list of [args...]")

        doc, code = self._getDocAndCode(form[2:])
        args = [x.name for x in form[1]]
    
        magicode = self._getMagicCodeForArgs(args)
        
        return ast.Lambda(args, [], magicode, code)
        

theCompiler = Compiler()

def sibpath(path, sibling):
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)

def makeNS(ns):
    global builtins
    if ns is None:
        ns = {}
    ns.update(builtins)
    return ns


def aeval(code, ns=None, filename='<Subol>'):
    ns = makeNS(ns)
    c = theCompiler
    ast = c.compileExpr(code)
    code = c.getCode(ast, mode='eval', filename=filename)
    return eval(code, ns)

def aexec(code, ns=None, filename='<Subol>'):
    ns = makeNS(ns)
    c = theCompiler
    ast = c.compileModule(code)
##    print "ast", ast
    code = c.getCode(ast, mode='exec', filename=filename)
##    import dis
##    dis.dis(code)
    return eval(code, ns)


def run(code, ns=None, mode='exec', filename='<Subol>'):
#    print "run!"
    p = Parser()
    code = p.parse(code)
##    import pprint
##    pprint.pprint(code)
    {'eval': aeval,
     'exec': aexec}[mode](code, ns=ns, filename=filename)

def runfile(filename, ns=None):
#    print "runfile!"
    run(open(filename).read(), ns=ns)

builtins = {}
# XXX *Weird* shit happens. This call is eating exceptions... somewhere
runfile(sibpath(__file__, 'builtins.sub'), ns=builtins)

import symbol

def prettifyAST(ast):
    code = ast[0]
    code = symbol.sym_name.get(code, code)
    return [code] + [isinstance(x, tuple) and prettifyAST(x) or x
                     for x in ast[1:]]

