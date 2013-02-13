import sys
from time import time
from copy import copy
from pprint import pprint

class Dejavu(object):
    def __init__(self):
        self.funcs = {}  # function call history
        self.rets = {}  # function return history
        self.locals = {}  # local var history
        self.globals = {} # globals history
        self.quitting = False
                 
    def trace_dispatch(self, frame, event, arg):
        if self.quitting:
            return # None
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
        return self.trace_dispatch

    def dispatch_call(self, frame, arg):
        t = time()
        record = (frame.f_lineno, 
                  frame.f_code.co_filename, 
                  frame.f_code.co_name)        
        self.funcs[t] = record 
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        t = time()
        record = (frame.f_lineno, 
                  frame.f_code.co_filename, 
                  frame.f_code.co_name,
                  copy(arg))        
        self.rets[t] = record
        return self.trace_dispatch

    def history(self, kind, entity):
       if kind not in ('locals','globals'):
          raise AttributeError("Only locals or globals are supported")
       struct = getattr(self, kind)
       h = [(t,d[1].get(entity,None)) for t,d in struct.items()]
       h.sort()
       return h
       
    def quit(self):
        self.quitting = True
        
if __name__=="__main__":
    prog_name = sys.argv[1]
    dejavu = Dejavu()
    sys.settrace(dejavu.trace_dispatch)
    prog_file = open(prog_name)
    exec prog_file
    dejavu.quit()
    
# python -i dejavu.py teste1.py
# dejavu.funcs 

