import math
var_global = 42

import teste2

def hipo(x,y):
   global var_global
   var_global = y
   return math.sqrt(teste2.soma(x**2, y**2))

if __name__=="__main__":
    pairs = zip(range(3,8),range(4,9))
    for i,j  in pairs:
        print(i,j,hipo(i,j))

