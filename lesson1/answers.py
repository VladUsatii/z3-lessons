#!/usr/bin/env python3
from z3 import Bool, And, Or, Not, Implies, Xor, Solver, sat, is_true

A = Bool("A") # "Enable FastPath"
B = Bool("B") # "Enable Caching"
C = Bool("C") # "Enable Auditing"
D = Bool("D") # "Enable Compression"

s = Solver()

"""
Constraints:
• A requires B
• D requires B or C
• Auditing and Caching can't both be enabled
• Either A or D is enabled but not both of them
• Compression must be enabled
"""

s.add(Implies(A, B))
s.add(Implies(D, Or(B, C)))
s.add(Not(And(B, C)))
s.add(Xor(A, D))
s.add(D)

r = s.check()
print("check() =", r)
if r == sat:
   m = s.model()
   for v in [A, B, C, D]:
      val = m.eval(v, model_completion=True)
      print(f"[-] {v} = {val}")
   print("[✔]")
else:
   print("[x] No configuration exists under the constraints.")
