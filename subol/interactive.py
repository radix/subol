from subol import sub2py, parse
import traceback, readline, sys

def collectForm():
    # XXX Ugh this will be less nasty once I properly stream-ize the
    # parser(s).
    p = parse.Parser()
    line = '\n' + raw_input("> ") + '\n'
    while 1:
        try:
            form = p.parse(line)
        except parse.ExpectedMore, e:
            lines = []
            while 1:
                i = raw_input('. ')
                if i == '':
                    break
                lines.append(i)
            line += '\n'.join(lines)
        else:
            return form


def interact():
    ns = {}
    while 1:
        try:
            code = collectForm()
            sub2py.aexec(code, ns=ns)
        except EOFError:
            sys.exit("\nBye!")
        except:
            traceback.print_exc()
