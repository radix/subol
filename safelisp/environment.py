# environment cruft

"""
SafeLisp environments are nested tuples, with dicts thrown in.

(None, {'x': 1})

Is an initial environment with a single frame containing a binding
from x to 1.

((None, {'x': 1}), {'y': 2})

Is the previous environment extended with another frame containing a
binding from y to 2.

Thisn structure is optimized for access / assignment to variables in
the current stack frame.

The terms "inner" and "outer" mean the youngest and oldest frames,
respectively. This can be confusing when considering the structure of
the environment, because new frames get wrapped around older
frames. Ignore that.
"""

__metaclass__ = type

class _Nothing: pass

def environment(init=None):
    """
    Create a new environment.

    @param init: If provided, specifies the initial bindings in the
           outermost frame.
    """
    if init is None:
        init = {}
    return (None, init)

def lookup(env, var):
    """
    Walk up the stack, looking in C{env} for C{var}.
    """
    val = None
    while 1:
        val = env[1].get(var, _Nothing)
        if val is not _Nothing:
            return val
        env = env[0]
        if env is None:
            raise NameError("variable '%s' not found" % var)


def pushFrame(env, frame):
    """
    Put a new frame on the stack.

    @type frame: C{dict}.
    """
    return (env, frame)


def set(env, var, val):
    """
    Set C{var} to C{val} in C{env}. This will either change the
    innermost variable named C{var} or create a new binding in the
    innermost frame. I think.
    """
    while 1:
        if env[1].has_key(var):
            env[1][var] = val
            return val
        if env[0] is None:
            raise NameError("Can't find %s for setting" % (var,))
        env = env[0]

def define(env, var, val):
    env[1][var] = val
