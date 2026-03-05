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

# ADD YOUR NEW REQUIREMENTS

# ---- Now we do a variant exploration with only assumptions ----

# Require D only

# ADD IT HERE

# Require A only

# ADD IT HERE

# Require both A and D

# ADD IT HERE

# Require A and D and not B

# ADD IT HERE

# Show push/pop for temporary edits (we'll do this one for you)
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

# EDIT THESE
s.add(S == ) # choose an S
s.add(n , m ) # choose some bounds for n and m
s.add(n + m == S) # same observable total size (we'll do this one for you)

# Two linear cost models
# • slow    = 5n + 1m
# • fast    = 1n + 3m
# • gap     = slow - fast = 4n - 2m = 6n - 2S . (m=S-n)

# DECLARE THEM IN Z3 AS INTS

# ADD THEM
s.add(slow == )
s.add(fast == )
s.add(gap == )

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

# Did you guess any of them correctly?
# Do you understand how we iterated through these boundaries to find our most approximate optimization?
