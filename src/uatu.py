# coding: utf-8

__nversion__ = (0, 0, 1)
__version__ = ".".join(str(i) for i in __nversion__)
__author__ = "rodsenra"

import sys
import dis
from time import time
from copy import copy
from pprint import pprint
from datetime import datetime

# Event types
EVENT_RESERVED = 0
EVENT_FUNC_CALL = 1
EVENT_FUNC_RET = 2
EVENT_ASSIGN = 3

EVENT_NAMES = ('reserved', 'call', 'return', 'assign')

# There must be only one uatu!
uatu = None


class Event(object):
    __slots__ = ('index', 'timestamp', 'event_type', 'obj_name', 'value')

    def __init__(self, index, timestamp, event_type, obj_name, value):
        self.index = index
        self.timestamp = timestamp
        self.event_type = event_type
        self.obj_name = obj_name
        self.value = value

    def __unicode__(self):
        return u"{0} {1:s} {2} {3} {4}".format(
            self.index,
            self.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            EVENT_NAMES[self.event_type],
            self.obj_name,
            self.value)

    def __repr__(self):
        return unicode(self)


class Uatu(object):

    def __init__(self, metadebug=False):
        self.metadebug = metadebug
        self.event_index = -1
        self.events = []
        # variable names whose values need to be captured asap
        self.pending_captures = []

    def trace_dispatch(self, frame, event, arg):
        if event == 'line':
            return self.dispatch_line(frame)
        elif event == 'call':
            return self.dispatch_call(frame, arg)
        elif event == 'return':
            return self.dispatch_return(frame, arg)
        return self.trace_dispatch

    def emit(self, event_type, objname, value):
        self.event_index += 1
        t = datetime.now()
        event = Event(self.event_index, t, event_type, objname, value)
        self.events.append(event)
        if self.metadebug:
            print("Event", event)

    def dispatch_line(self, frame):
        # generate events for pending variables from previous lines
        while self.pending_captures:
            varname = self.pending_captures.pop(0)
            try:
                value = frame.f_locals[varname]
                self.emit(EVENT_ASSIGN, varname, value)
            except KeyError:
                if self.metadebug:
                    print "Ignoring", varname
                    # value not available yet
                break

        new_code = self.cut_asm(frame.f_lasti, frame.f_code)
        self.schedule_capture(frame.f_lasti, frame, new_code)

        if self.metadebug:
            record = (frame.f_lineno,
                      "line",
                      frame.f_code.co_filename,
                      frame.f_code.co_name)
            pprint(record)

        return self.trace_dispatch

    def dispatch_call(self, frame, arg):
        # Arg names are mixed with local variables,
        #  but come first in the list co_varnames
        arg_names = frame.f_code.co_varnames[:frame.f_code.co_argcount]
        call_params = {name: frame.f_locals[name] for name in arg_names} \
            if (frame.f_code.co_name != '<module>') \
            else ''

        record = (frame.f_lineno,
                  frame.f_code.co_filename,
                  frame.f_code.co_name,
                  call_params,
                  copy(arg))
        self.emit(EVENT_FUNC_CALL, frame.f_code.co_name, record)
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        t = time()
        record = (frame.f_lineno,
                  frame.f_code.co_filename,
                  copy(arg))
        self.emit(EVENT_FUNC_RET, frame.f_code.co_name, record)
        return self.trace_dispatch

    def cut_asm(self, line, code):
        if line == -1:
            # ignore
            return code

        first = 0
        last = codesize = len(code.co_code)
        lines = list(dis.findlinestarts(code))
        for pos, (asm_line, src_line) in enumerate(lines):
            if line != asm_line:
                continue
            else:
                if asm_line == lines[-1][0]:
                    first, last = (asm_line, codesize)
                else:
                    first, last = (asm_line, lines[pos+1][0])
                break

        codestr = code.co_code[first:last]

        # Rebuild code object
        new_code = type(code)(code.co_argcount,
                              code.co_nlocals,
                              code.co_stacksize,
                              code.co_flags,
                              codestr,
                              code.co_consts,
                              code.co_names,
                              code.co_varnames,
                              code.co_filename,
                              code.co_name,
                              code.co_firstlineno,
                              code.co_lnotab,
                              code.co_freevars,
                              code.co_cellvars)

        if self.metadebug:
            dis.disassemble(new_code)

        return new_code

    def schedule_capture(self, line, frame, co):
        # co param may be different from frame.f_code
        store_codes = [dis.opmap[i] for i in ('STORE_FAST',  'STORE_NAME')]
        # TODO: support 'STORE_GLOBAL', 'STORE_MAP','STORE_ATTR'
        code = co.co_code
        n = len(code)
        i = 0
        while i < n:
            c = code[i]
            op = ord(c)
            i = i + 1
            if op >= dis.HAVE_ARGUMENT:
                i = i + 2
                if op in store_codes:
                    arg = ord(code[i-2]) | (ord(code[i-1]) << 8)
                if op == dis.opmap['STORE_FAST']:
                    varname = co.co_varnames[arg]
                    self.pending_captures.append(varname)
                elif op == dis.opmap['STORE_NAME']:
                    varname = co.co_names[arg]
                    self.pending_captures.append(varname)


def install(metadebug):
    global uatu
    if uatu is None:
        uatu = Uatu(metadebug=metadebug)
        sys.settrace(uatu.trace_dispatch)


def uninstall():
    sys.settrace(None)


def watch(py_file):
    #uatu = Uatu()
    install(metadebug=True)
    try:
        exec py_file
    finally:
        # do not call uninstall to exit cleanly
        sys.settrace(None)


if __name__ == "__main__":
    module_name = sys.argv[1]
    py_file = open(module_name)
    watch(py_file)
    py_file.close()
    # useful for interactive mode -i, and harmless otherwise
    from pprint import pprint as pp

# uatu.py must be in the PYTHONPATH
# export PYTHONPATH=`pwd`/src:$PYTHONPATH
# cd samples
# python -i -m uatu teste0.py
# >>> pp(uatu.events)
