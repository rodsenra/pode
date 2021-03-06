# coding: utf-8

__nversion__ = (0, 0, 2)
__version__ = ".".join(str(i) for i in __nversion__)
__author__ = "rodsenra"

import sys
import dis
from time import time
from copy import copy
from pprint import pprint
from datetime import datetime
from inspect import getfile

import redis # pip install redis hiredis

# Event types
EVENT_RESERVED = 0
EVENT_FUNC_CALL = 1
EVENT_FUNC_RET = 2
EVENT_ASSIGN = 3

# CAPTURE_TYPES
CAP_LOCAL = 1
CAP_GLOBAL = 2

# AUXILIARY EXTRACTION FUNCTIONS
def _const_arg(co, arg):
    return co.co_varnames[arg]

def _name_arg(co, arg):
    return co.co_names[arg]

# Dictionary of fucntions to extract opcode argument values
GET_ARGS = {dis.opmap["LOAD_CONST"]: _const_arg,
            dis.opmap["LOAD_NAME"]: _name_arg,}

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

    def set(self, redis):
        redis.set(self.index, (self.timestamp, self.event_type, self.obj_name, self.value))

    def __repr__(self):
        return unicode(self)


class Uatu(object):

    def __init__(self, metadebug=False):
        self.redis = redis.StrictRedis(unix_socket_path='/tmp/redis.sock')
        self.redis.flushdb()

        self.metadebug = metadebug
        self.event_index = -1
        self.events = []
        # (variable names, scope) whose values need to be captured asap
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
        event.set(self.redis)
        self.events.append(event)
        if self.metadebug:
            print("Event", event)

    def capture_value(self, frame):
        # generate events for pending variables from previous lines
        while self.pending_captures:
            varname, scope = self.pending_captures.pop(0)
            try:
                if scope == CAP_LOCAL:
                    value = frame.f_locals[varname]
                    self.emit(EVENT_ASSIGN, varname, value)
                elif scope == CAP_GLOBAL:
                    value = frame.f_globals[varname]
                    self.emit(EVENT_ASSIGN, varname, value)
                else:
                    print "Ignored", varname

            except KeyError:
                if self.metadebug:
                    print "Ignoring", varname
                    # value not available yet
                break

    def dispatch_line(self, frame):
        self.capture_value(frame)
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

        p = getfile(frame)
        print(">>>>" + p)
        co_name = frame.f_code.co_name
        if co_name == "<module>":
            record = (frame.f_lineno,
                      frame.f_code.co_filename)
        else:
            record = (frame.f_lineno,
                      frame.f_code.co_filename,
                      co_name,
                      call_params,
                      copy(arg))
        self.emit(EVENT_FUNC_CALL, frame.f_code.co_name, record)
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        self.capture_value(frame)
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
                    first, last = (asm_line, lines[pos + 1][0])
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
        store_codes = [dis.opmap[i] for i in ('LOAD_NAME', 'LOAD_CONST', 'STORE_FAST', 'STORE_NAME', 'STORE_GLOBAL')]
        # TODO: support 'STORE_MAP','STORE_ATTR'
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
                    arg = ord(code[i - 2]) | (ord(code[i - 1]) << 8)

                if op == dis.opmap['STORE_FAST']:
                    varname = co.co_varnames[arg]
                    self.pending_captures.append((varname, CAP_LOCAL))
                elif op == dis.opmap['STORE_GLOBAL']:
                    varname = co.co_names[arg]
                    self.pending_captures.append((varname, CAP_GLOBAL))
                elif op == dis.opmap['STORE_NAME']:
                    varname = co.co_names[arg]
                    self.pending_captures.append((varname, CAP_LOCAL))


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
        # Create isolated dictionaries for globals() and locals() to be used by the inferior process
        # When executed from command-line must emulate __main__ module __name__
        exec py_file in globals() #{}, {'__name__':'__main__'}
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

# if this is your first install, automatically load on login with:
#     mkdir -p ~/Library/LaunchAgents
#     cp /usr/local/Cellar/redis/2.4.17/homebrew.mxcl.redis.plist ~/Library/LaunchAgents/
#     launchctl load -w ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
#      To start redis manually:
#      redis-server /usr/local/etc/redis.conf
#
#      To access the server:
#      redis-cli

# /usr/local/bin/redis-server /usr/local/etc/redis.conf
# uatu.py must be in the PYTHONPATH
# export PYTHONPATH=`pwd`/src:$PYTHONPATH
# cd samples
# python -i -m uatu teste0.py
# >>> pp(uatu.events)
