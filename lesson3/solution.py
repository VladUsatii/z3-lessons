from z3 import *

print("Int vs. BitVec")

x = Int("xI")
s = Solver()
s.add(x == 255 + 1)
assert s.check() == sat
m = s.model()
print("Int: 255 + 1 =", m.eval(x))

del x, s, m

x = BitVec("xB", 8)
s = Solver()
s.add(x == BitVecVal(255, 8) + BitVecVal(1, 8))
assert s.check() == sat
m = s.model()
# You can expect that a wrapping will occur from 0 for the 8-bit
print("BitVec8: 255 + 1 =", m.eval(x), "(decimal:", m.eval(x).as_long(), ")")

del x, s, m

print("Arrays (Store and Select)")

A = Array("A", IntSort(), IntSort()) # Z -> Z
i = Int("i")
s = Solver()

# AN = Store(A, X, Y): write Y to key X
A1 = Store(A, 5, 99)
A2 = Store(A, 6, 102)

# Property: reading back at 5 gives 99
s.add(Select(A1, 5) != 99)
r = s.check()
print(f"Negating read after write should yield: {r} (unsat)")

# Let's do a SAT query this time
s2 = Solver()
s2.add(i != 5)
s2.add(Select(A1, i) == Select(A, i))
r2 = s2.check()
m = s2.model()
print(f"SAT: {r2}  {m}")

del A, i, s, A1, A2, r, s2, r2, m

print("Uninterpreted functions (UF)")

f = Function("f", IntSort(), IntSort()) # Z -> Z
x, y = Ints("x y")
s = Solver()

# Congruence property
s.add(x == y)
s.add(f(x) != f(y))
r = s.check()
print("x==y but f(x) != f(y) should yield unsat: ", r)

# But f has no further semantics, so it can still satisfy f(0) = 1, f(1) = 1, etc.
s2 = Solver()
s2.add(f(0) == 1)
s2.add(f(1) == 1)
print("UF can map different inputs to the same output: ", s2.check(), " (should be sat)")

del f, x, y, s, r, s2

print("Enumerate models with blocking clauses")

a, b, c = Bools("a b c")
s = Solver()

# With PbEq, exactly one of a,b,c is true
s.add(PbEq([(a, 1), (b, 1), (c, 1)], 1))

models = []
while s.check() == sat:
   m=s.model()
   va = is_true(m.eval(a, model_completion=True))
   vb = is_true(m.eval(b, model_completion=True))
   vc = is_true(m.eval(c, model_completion=True))
   models.append((va, vb, vc))
   print("model: ", (va, vb, vc))

   # block that assignment over (a,b,c)
   block = Or(a != va, b != vb, c != vc)
   s.add(block)

print("Total models found:", len(models), "(should be 3)")
