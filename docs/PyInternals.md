Introduction
============

This file documents topics from Python internals that are relevant to the implementation
of the Python Omniscient Debugger.

The hook: sys.settrace
----------------------

The function [sys.settrace](http://docs.python.org/3/library/sys.html#sys.settrace) is used
to define a Python level function for debugging purposes.
The function is thread specific, and must be set in all threads independently.

Trace functions should have three arguments: frame, event, and arg. frame is the current stack frame.
event is a string: 'call', 'line', 'return', 'exception', 'c_call', 'c_return', or 'c_exception'.
arg depends on the event type.

The events have the following meaning:

'call'
A function is called (or some other code block entered).
The global trace function is called; arg is None; the return value specifies the local trace function.

'line'
The interpreter is about to execute a new line of code or re-execute the condition of a loop.
The local trace function is called; arg is None; the return value specifies the new local trace function.
See Objects/lnotab_notes.txt for a detailed explanation of how this works.

'return'
A function (or other code block) is about to return.
The local trace function is called; arg is the value that will be returned, or None if the event is caused by an exception being raised.
The trace function’s return value is ignored.

'exception'
An exception has occurred.
The local trace function is called; arg is a tuple (exception, value, traceback); the return value specifies the new local trace function.

'c_call'
A C function is about to be called.
This may be an extension function or a built-in. arg is the C function object.

'c_return'
A C function has returned. arg is the C function object.

'c_exception'
A C function has raised an exception. arg is the C function object.


Inside sys.settrace
-------------------

In the source tree Python-2.7.3/Python/sysmodule.c we find the implementation
of sys.settrace:

```C
static PyObject *
sys_settrace(PyObject *self, PyObject *args)
{
    if (trace_init() == -1)
        return NULL;
    if (args == Py_None)
        PyEval_SetTrace(NULL, NULL);
    else
        PyEval_SetTrace(trace_trampoline, args);
    Py_INCREF(Py_None);
    return Py_None;
}
```

The interesting part is the call to trace_trampoline, whose definition is:

```C
static int
trace_trampoline(PyObject *self, PyFrameObject *frame,
                 int what, PyObject *arg)
{
    PyThreadState *tstate = frame->f_tstate;
    PyObject *callback;
    PyObject *result;

    if (what == PyTrace_CALL)
        callback = self;
    else
        callback = frame->f_trace;
    if (callback == NULL)
        return 0;
    result = call_trampoline(tstate, callback, frame, what, arg);
    if (result == NULL) {
        PyEval_SetTrace(NULL, NULL);
        Py_XDECREF(frame->f_trace);
        frame->f_trace = NULL;
        return -1;
    }
    if (result != Py_None) {
        PyObject *temp = frame->f_trace;
        frame->f_trace = NULL;
        Py_XDECREF(temp);
        frame->f_trace = result;
    }
    else {
        Py_DECREF(result);
    }
    return 0;
}
```

This function delegates execution to call_trampoline:

```C
static PyObject *
call_trampoline(PyThreadState *tstate, PyObject* callback,
                PyFrameObject *frame, int what, PyObject *arg)
{
    PyObject *args = PyTuple_New(3);
    PyObject *whatstr;
    PyObject *result;

    if (args == NULL)
        return NULL;
    Py_INCREF(frame);
    whatstr = whatstrings[what];
    Py_INCREF(whatstr);
    if (arg == NULL)
        arg = Py_None;
    Py_INCREF(arg);
    PyTuple_SET_ITEM(args, 0, (PyObject *)frame);
    PyTuple_SET_ITEM(args, 1, whatstr);
    PyTuple_SET_ITEM(args, 2, arg);

    /* call the Python-level function */
    PyFrame_FastToLocals(frame);
    result = PyEval_CallObject(callback, args);
    PyFrame_LocalsToFast(frame, 1);
    if (result == NULL)
        PyTraceBack_Here(frame);

    /* cleanup */
    Py_DECREF(args);
    return result;
}
```
