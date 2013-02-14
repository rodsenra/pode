import sys
import dis
from time import time
from copy import copy
from pprint import pprint

class Dejavu(object):
    def __init__(self):
        self.calls = {}  # function call/return history
        self.locals = {}  # local var history
        self.globals = {} # globals history

    def trace_dispatch(self, frame, event, arg):
        if event == 'line':
            return self.dispatch_line(frame)
        if event == 'call':
            return self.dispatch_call(frame, arg)
        if event == 'return':
            return self.dispatch_return(frame, arg)
        return self.trace_dispatch

    def dispatch_line(self, frame):
        t = time()
        self.locals[t] = (frame.f_lineno, copy(frame.f_locals))
        self.globals[t] = (frame.f_lineno, copy(frame.f_globals))
        record = (frame.f_lineno,
                  "line",
                  frame.f_code.co_filename,
                  frame.f_code.co_name)
        pprint(record)
        self.dump_asm(frame.f_lasti, frame.f_code)
        self.fetch_opcodes(frame.f_lasti, frame.f_code)

        return self.trace_dispatch

    def dispatch_call(self, frame, arg):
        t = time()
        # Arg names are mixed with local variables, but come first in the list co_varnames
        arg_names = frame.f_code.co_varnames[:frame.f_code.co_argcount]
        call_params = {name:frame.f_locals[name] for name in arg_names} \
                      if (frame.f_code.co_name != '<module>') \
                      else ''
        record = (frame.f_lineno,
                  "call",
                  frame.f_code.co_filename,
                  frame.f_code.co_name,
                  call_params,
                  copy(arg))
        self.calls[t] = record
        pprint(record)
        self.dump_asm(frame.f_lasti, frame.f_code)
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        t = time()
        record = (frame.f_lineno,
                  "ret",
                  frame.f_code.co_filename, 
                  frame.f_code.co_name,
                  copy(arg))        
        self.calls[t] = record
        pprint(record)
        return self.trace_dispatch

    def history(self, kind, entity):
       if kind not in ('locals','globals'):
          raise AttributeError("Only locals or globals are supported")
       struct = getattr(self, kind)
       h = [(t,d[1].get(entity,None)) for t,d in struct.items()]
       h.sort()
       return h

    def dump_asm(self, line, code):
        print("Line {0}".format(line))
        dis.disassemble(code)

    def fetch_opcodes(self, line, co):
        code = co.co_code
        n = len(code)
        linestarts = dict(dis.findlinestarts(co))
        print "linestarts", linestarts
        i = 0
        while i < n:
            c = code[i]
            op = ord(c)
            print "Op", dis.opname[op]
            i = i + 1
            if op >= dis.HAVE_ARGUMENT:
                i = i + 2

if __name__=="__main__":
    prog_name = sys.argv[1]
    dejavu = Dejavu()
    sys.settrace(dejavu.trace_dispatch)
    prog_file = open(prog_name)
    exec prog_file
    sys.settrace(None)
    # useful for interactive mode -i
    from pprint import pprint as pp

# python -i dejavu.py teste1.py
# >> pp(dejavu.calls)

