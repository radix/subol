from safelisp import interpreter, parse, context
import traceback, readline, sys

def collectForm(p):
    line = raw_input("> ") + '\n'
    while 1:
        try:
            return p.parse(line)
        except parse.ExpectedMore, e:
            i = raw_input('. ') + '\n'
            if i == '\n':
                continue
            line += i

def interact():
    p = parse.Parser()
    interp = interpreter.defaultInterpreter()
    context.call({'SL-interp': interp}, _reallyInteract, p, interp)

def _reallyInteract(p, interp):
    env = interpreter.defaultEnvironment()
    while 1:
        try:
            try:
                code = collectForm(p)
            except SyntaxError, e:
                print e
            else:
                for x in code:
                    v = interp.eval(x, env)
                    if v is not None:
                        print v

        except EOFError:
            sys.exit("\nBye!")
        except:
            traceback.print_exc()
