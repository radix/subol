from safelisp import objects as O, environment as E

def special_set(interp, form, env):
    lit = form.pyvalue
    value = interp.evalForm(lit[2], env)
    E.set(env, lit[1].name, value)
    return value

def special_def(interp, form, env):
    lit = form.pyvalue
    value = interp.evalForm(lit[2], env)
    E.define(env, lit[1].name, value)
    return value

def special_lambda(interp, form, env):
    lit = form.pyvalue
    lambdalist = lit[1].pyvalue
    body = lit[2:]
    value = O.Function(O.String('<lambda>'), lambdalist, body, env)
    return value

def _funcOrMac(interp, form, env, funcormac):
    lit = form.pyvalue
    lambdalist = lit[1].pyvalue
    name = lambdalist.pop(0).name
    body = lit[2:]
    value = funcormac(O.String(name), lambdalist, body, env)
    E.define(env, name, value)
    return value

def special_defmacro(interp, form, env):
    return _funcOrMac(interp, form, env, O.Macro)

def special_defun(interp, form, env):
    return _funcOrMac(interp, form, env, O.Function)

def special_let(interp, oform, env):
    "(let bindings &body)"
    form = oform.pyvalue
    bindings = form[1].pyvalue
    body = form[2:]
    d = {}
    for binding in bindings:
        name, value = binding.pyvalue
        d[name.name] = interp.evalForm(value, env)
    newEnv = E.pushFrame(env, d)
    r = None
    for code in body:
        r = interp.evalForm(code, newEnv)
    return r

def special_I(interp, form, env):
    return form.pyvalue[1]

def special_for(interp, form, env):
    # XXX! Put this in a separate cap.
    form = form.pyvalue
    name = form[1].name
    result = []
    for x in interp.evalForm(form[2], env).pyvalue:
        E.define(env, name, x)
        r = None
        for chunk in form[3:]:
            r = interp.evalForm(chunk, env)
        result.append(r)
    return O.List(result)

def getSpecials():
    d = {}
    for name,obj in globals().items():
        if name.startswith('special_'):
            d[name[len('special_'):]] = obj
    return d

