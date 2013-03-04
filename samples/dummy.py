import sys
module_name = sys.argv[1]
py_file = open(module_name)
#exec py_file in globals() #, {"__name__":"__main__"}
exec py_file in globals()

