from z3 import *

print("Int vs. BitVec")

xI = Int("xI")
sI = Solver()
sI.add(xI == 255 + 1)
assert sI.check() == sat
mI = sI.model()
print("Int: 255 + 1 =", mI.eval(xI))

xB = BitVec("xB", 8)
sB = Solver()

