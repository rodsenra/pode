pode
====

**pode** stands for Python Omniscient Debugger.

Feel free to join the discussion [via email](mailto:pode_py@googlegroups.com)
or  browse the [discussion group](https://groups.google.com/forum/?fromgroups#!forum/pode_py).

About
=======

It all began in 1969, when Bob Balzer implemented a version of omniscient debugging for Fortran.

From [1]:

> Omniscient debugging describes the concept that debuggers should know everything about the run of a program,
> that they should remember every state change, and be able to present to you the value of any variable at any
> point in time. Essentially, omniscient debugging means that you can go backwards in time.

Inspired by the article "Omniscient Debbuging - an easier way to find program bugs" by Bil Lewis [1],
I decided to explore the issue in Python.
This project is an informal exploration on the subject.



Architecture
============

    +----------+   +----------+    +-------+   +---------+
    | Inferior |==>| Event    |==> | Event |<->|  Info   |
    | Process  |   | Recorder |    |   DB  |   | Browser |
    +----------+   +----------+    +-------+   +---------+

 The process being debugged is called the **inferior process**.
 The **event recorder** is responsible for monitoring the inferior processes to detect events.
 These events are recorded in the **event database**.
 The **info browser** queries the event database and displays information related to the recorded events.


Strategies
==========

My first strategy is to leverage sys.settrace as the main hook in the Python Virtual Machine (PVM) to record events.
A function registered with sys.settrace will act as event recorder.
There can be many event database backends. The main requirement is support for fast data insertions (write operations).
I would like to explore Redis, ElasticSearch and Neo4J as backends.
Moreover, I will use a regular Web browser to build the *info browser*.

For the time being, we are not resorting to application code instrumentation.


Related Work
============

 * [pdb](http://docs.python.org/2/library/pdb.html)
 * [ipdb](http://pypi.python.org/pypi/ipdb)
 * [pydb](http://bashdb.sourceforge.net/pydb/)
 * [pydbgr](http://code.google.com/p/pydbgr/)
 * [winpdb, rpdb2](http://winpdb.org/)
 * [TOD](http://pleiad.dcc.uchile.cl/tod/) is a portable Trace-Oriented Debugger for Java integrated into the Eclipse IDE.
   See "Scalable Omniscient Debugging" by Guillaume Pothier, Éric Tanter and José Piquer.


References
==========

Several articles examined are included in the directory docs/external.

[1] "Omniscient Debbuging - an easier way to find program bugs".
     Bil Lewis. Dr. Dobbs Journal.   June 2005.
