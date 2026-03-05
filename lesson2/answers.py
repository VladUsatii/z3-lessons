from z3 import Bool, Int, And, Or, Not, Implies, Solver, sat, unsat

# ============ Exercise 1: Incremental solving and cores ============
print("Exercise 1")

A = Bool("A")
B = Bool("B")
C = Bool("C")
D = Bool("D")

s = Solver()

s.add(Implies(A, B))
s.add(Implies(D, Or(B, C)))
s.add(Not(And(B, C)))
s.add(Or(A, D))
s.add(Not(And(A, D)))

# Requirements are gated by assumption literals
req_A = Bool("req_A")
req_D = Bool("req_D")
req_noB = Bool("req_noB")

# To do this correctly, wrap your requirements in Implies to their correct variable
s.add(Implies(req_A, A))
s.add(Implies(req_D, D))
s.add(Implies(req_noB, Not(B)))

# ---- Now we do a variant exploration with only assumptions ----

# Require D only
r1 = s.check(req_D)
print("[Bool] require D only: ", r1)

# Require A only
r2 = s.check(req_A)
print("[Bool] require A only: ", r2)

# Require both A and D
r3 = s.check(req_A, req_D)
print("[Bool] require A and D: ", r3)
if r3 == unsat: print("  unsat core: ", s.unsat_core())

# Require A and D and not B
r4 = s.check(req_A, req_D, req_noB)
print("[Bool] require A and D and not-B:", r4)
if r4 == unsat: print("  unsat core: ", s.unsat_core())

# Show push/pop for temporary edits
s.push()
s.add(B) # temporary additional constraint added
s.add(C) # another one that violates Not(And(B,C))
r5 = s.check(req_D)
print("[Bool] under temporary B=true, C=true, require D: ", r5)

del s

# ============ Exercise 2: Gap threshold search ============
print("Exercise 2")

s = Solver()

# Observable size (projection Π): total size S is fixed
S = Int("S")
n = Int("n")
m = Int("m")

# Domain constraints
s.add(S == 50) # choose an S
s.add(n >= 0, m >= 0) # choose some bounds for n and m
s.add(n + m == S) # same observable total size

# Two linear cost models
# • slow    = 5n + 1m
# • fast    = 1n + 3m
# • gap     = slow - fast = 4n - 2m = 6n - 2S . (m=S-n)
slow = Int("slow")
fast = Int("fast")
gap = Int("gap")

s.add(slow == 5*n + 1*m)
s.add(fast == n + 3*m)
s.add(gap == slow - fast)

# Gap threshold search: find the largest K s.t. SAT(gap >= K)

# We are avoiding optimization for now, so we'll use iterative SAT checks
print("[Int] Testing several K values:")
for K in [0, 50, 100, 150, 200, 210]:
   s.push()
   s.add(gap >= K)
   r = s.check()
   model = None
   if r == sat: model = s.model()
   s.pop()

   print(f"  K={K}: {r}", end=" ")
   if r == sat:
      nn = model.eval(n, model_completion=True)
      mm = model.eval(m, model_completion=True)
      gg = model.eval(gap, model_completion=True)
      print(f"  witness: n={nn}  m={mm}  gap={gg}")
   else: print("")

best = None
for K in range(0,221):
   s.push()
   s.add(gap >= K)
   r = s.check()
   model = None
   if r == sat: model = s.model()
   s.pop()
   if r == sat: best = K
print(f"[Int] Max satisfiable K in [0,220] is: {best}")
