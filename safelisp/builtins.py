import sys, operator

from safelisp import interpreter
from safelisp import objects as O
from safelisp import context

## Builtin Functions ##

def func_println(*args):
    func_print(*args)
    sys.stdout.write('\n')

def func_print(*args):
    sys.stdout.write(str(O.simplify(args[0])))
    for x in args[1:]:
        sys.stdout.write(' ')
        sys.stdout.write(str(O.simplify(x)))


def func_index(o, i):
    return o.__sl_index__(i)


def func_slice(seq, begin, end):
    return O.List(seq.pyvalue[slice(O.simplify(begin), O.simplify(end))])


def func_vec(*args):
    return O.List(list(args))

#whooaoh, bad name. Wait, why is it a bad name?
def func_dict(*args):
    assert (len(args) % 2) == 0, "need even number of args"
    d = {}
    args = list(args)
    while args:
        k = args.pop(0)
        v = args.pop(0)
        d[k] = v
    return O.Dict(d)


def func_getattr(o, name):
    name = name.pyvalue
    if not hasattr(o, 'sl_getAttribute'):
        raise ValueError("%r is not an SLObject." % o)
    return o.sl_getAttribute(name)


def func_setattr(o, name, value):
    name = name.pyvalue
    if not hasattr(o, 'sl_setAttribute'):
        raise ValueError("%r is not an SLObject." % o)
    return o.sl_setAttribute(name, value)


# funcs that will have names that aren't valid python identifiers: see
# builtins assignment below

def add(*args):
    v = O.py2SLO(reduce(operator.add, [x.pyvalue for x in args]))
    return v

def sub(*args):
    v = O.py2SLO(reduce(operator.sub, [x.pyvalue for x in args]))
    return v

def mul(*args):
    v = O.py2SLO(reduce(operator.mul, [x.pyvalue for x in args]))
    return v

def div(*args):
    v = O.py2SLO(reduce(operator.div, [x.pyvalue for x in args]))
    return v

def eq(o1, o2):
    return O.simplify(o1) == O.simplify(o2)

def func_dir():
    env = context.get('SL-env')
    # XXX show specials here too. Or maybe make specials a part of the environment! wee hee.
    d = env[1].copy()

    # hmm, ok, even though vars from lower on the stack will
    # "overwrite" ones from above it, it doesn't matter, because we
    # only care about the names here, not objects.
    while 1:
        env = env[0]
        if env == None: break
        d.update(env[1])
    return d.keys()



builtins = {
    '+': add,
    '-': sub,
    '*': mul,
    '/': div,
    '==': eq,
    '*exc-handler*': interpreter.print_traceback,
    'None': None,
    # XXX maybe this in a separate cap -- maybe setattr in a separate cap
    'make-object': O.SLObject,
    }


def getFunctions():
    d = builtins.copy()
    for name,obj in globals().items():
        if name.startswith('func_'):
            d[name[5:]] = obj
    return d

