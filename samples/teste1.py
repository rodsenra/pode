import math
var_global = 42

# import teste2
from teste2 import soma
print("GLOBALS" + str(globals().keys()))
print("LOCALS" + str(locals().keys()))

def hipo(x,y):
   global var_global
   var_global = y
   #print("GLOBALS" + str(globals().keys()))
   #print("LOCALS" + str(locals().keys()))
   quadrado = soma(x**2, y**2)
   return math.sqrt(quadrado)

if __name__=="__main__":
    pairs = zip(range(3,8), range(4,9))
    for i,j  in pairs:
        print("result", i, j, hipo(i,j))

