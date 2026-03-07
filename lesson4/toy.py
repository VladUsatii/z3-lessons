#!/usr/bin/env python3
# toy.py
# Two-trace gap analysis in Z3 using CEGAR.
from z3 import *
from colorama import Fore, Style, init

# ================= Parameters =================

# Operations
INS = 0      # Costs 1
DEL = 1      # Costs current size

M = int(input("Input M: "))        # Number of keys: {0, 1} for now
L = int(input("Input L: "))        # Trace length (must be even so size==0 is possible)
N = L // 2

# Rough upper bound on max gap for this toy cost model
K_upper = N * (N-1) // 2

# CEGAR refinement lemmas can accumulate across K checks
refinements = []
max_refine = 500

# Search for the best K value
bestK = None
bestW = None

# ================== NEW: tiny colored print helpers ==================

def C(c, s): return c + s + Style.RESET_ALL
def ok(s):  print(C(Fore.GREEN,  s))
def bad(s): print(C(Fore.RED,    s))
def inf(s): print(C(Fore.CYAN,   s))
def warn(s):print(C(Fore.YELLOW, s))
def dim(s): print(C(Fore.WHITE + Style.DIM, s))
def fmt_trace(ops, keys): return " ".join(("I" if o == INS else "D") + str(int(k)) for o, k in zip(ops, keys))
def extract_sizes(model, size_vars, L): return [int(model.eval(size_vars[t], model_completion=True).as_long()) for t in range(L+1)]

# Compute per-key counts prefix evolution (for explaining violations)
def prefix_counts(M, ops, keys, upto_t):
   cnt = [0]*M
   for t in range(upto_t+1):
      k = int(keys[t])
      if ops[t] == INS: cnt[k] += 1
      else: cnt[k] -= 1
   return cnt

# Totals for Π sanity display (ins/del counts per key)
def totals_per_key(M, ops, keys):
   ins, dele = [0]*M, [0]*M
   for o,k in zip(ops, keys):
      if o == INS: ins[int(k)] += 1
      else: dele[int(k)] += 1
   return ins, dele

# ================ Build the base Z3 problem ================

def mk_base_problem(M, L, refinements):
   s = Solver()

   # Decision variables: op[tr][t] in {INS, DEL}; key[tr][t] in {0..M-1}
   op  = [[Int(f"op_{tr}_{t}") for t in range(L)] for tr in range(2)]
   key = [[Int(f"key_{tr}_{t}") for t in range(L)] for tr in range(2)]

   # Abstract total multiset size state for each trace (L + 1 states for L steps)
   size = [[Int(f"size_{tr}_{t}") for t in range(L + 1)] for tr in range(2)]

   # Cost and total cost per step
   step_cost  = [[Int(f"c_{tr}_{t}") for t in range(L)] for tr in range(2)]
   total_cost = [Int("total_cost_0"), Int("total_cost_1")]

   # (1) Domain constraints and abstract validity
   for tr in range(2):
      s.add(size[tr][0] == 0)

      for t in range(L):
         s.add(Or(op[tr][t] == INS, op[tr][t] == DEL))
         s.add(And(key[tr][t] >= 0, key[tr][t] < M))
         s.add(size[tr][t + 1] == size[tr][t] + If(op[tr][t] == INS, 1, -1))
         s.add(size[tr][t] >= 0)
         s.add(size[tr][t + 1] >= 0)
         s.add(Implies(op[tr][t] == DEL, size[tr][t] >= 1))
         s.add(step_cost[tr][t] == If(op[tr][t] == INS, 1, size[tr][t]))

      s.add(size[tr][L] == 0)
      s.add(total_cost[tr] == Sum(step_cost[tr]))

   # (2) Projection / comparability Π: same totals per key of INS/DEL across traces
   for k in range(M):
      ins0 = Sum([If(And(op[0][t] == INS, key[0][t] == k), 1, 0) for t in range(L)])
      ins1 = Sum([If(And(op[1][t] == INS, key[1][t] == k), 1, 0) for t in range(L)])
      del0 = Sum([If(And(op[0][t] == DEL, key[0][t] == k), 1, 0) for t in range(L)])
      del1 = Sum([If(And(op[1][t] == DEL, key[1][t] == k), 1, 0) for t in range(L)])
      s.add(ins0 == ins1)
      s.add(del0 == del1)

   # (3) Apply the learned refinements (CEGAR lemmas)
   for c in refinements: s.add(c)

   return s, op, key, size, total_cost

def prefix_count_expr(op, key, tr, k, t, L, kind):
   terms = []
   for u in range(t+1): terms.append(If(And(op[tr][u] == kind, key[tr][u] == k), 1, 0))
   return Sum(terms)

def extract_trace(model, op, key, L):
   return [model.eval(op[t], model_completion=True).as_long() for t in range(L)], \
          [model.eval(key[t], model_completion=True).as_long() for t in range(L)]

def simulate_cost(ops, keys):
   size, total = 0, 0
   for o in ops:
      if o == INS:
         total += 1
         size  += 1
      else:
         total += size
         size  -= 1
   return total

def refine_lemma(op, key, tr, bad_step, bad_key, L):
   ins_pref = prefix_count_expr(op, key, tr, bad_key, bad_step, L, INS)
   del_pref = prefix_count_expr(op, key, tr, bad_key, bad_step, L, DEL)
   return (ins_pref - del_pref) >= 0

def validate_concrete(M, ops, keys):
   counts = [0] * M
   for t, (o, k) in enumerate(zip(ops, keys)):
      k = int(k)
      if o == INS: counts[k] += 1
      else:
         counts[k] -= 1
         if counts[k] < 0: return (t, k)
   return None

def find_witness_for_K(M, L, K, refinements):
   # NEW: show start of feasibility check
   inf(f"\n[feasible?] K={K}  current_refinements={len(refinements)}")

   for it in range(1, max_refine+1):
      # NEW: small progress marker
      dim(f"  (cegar iter {it}) building+solving abstraction...")

      s, op, key, size, total_cost = mk_base_problem(M, L, refinements)
      s.add(total_cost[0] - total_cost[1] >= K)

      r = s.check()
      if r == unsat:
         bad(f"  UNSAT at K={K} (after {it-1} refinements inside this K-check)")
         return False, None, refinements
      if r != sat:
         raise RuntimeError(f"Z3: {r}")

      m = s.model()

      ops0, keys0 = extract_trace(m, op[0], key[0], L)
      ops1, keys1 = extract_trace(m, op[1], key[1], L)

      # NEW: extract and print size trajectories (this is where “cost” comes from)
      sz0 = extract_sizes(m, size[0], L)
      sz1 = extract_sizes(m, size[1], L)

      # NEW: show witnesses compactly
      c0 = simulate_cost(ops0, keys0)
      c1 = simulate_cost(ops1, keys1)
      gap = c0 - c1

      ok(f"  SAT model found: gap={gap} (needs ≥ {K})  cost0={c0} cost1={c1}")
      dim(f"    τ0: {fmt_trace(ops0, keys0)}")
      dim(f"    sz0: {sz0}")
      dim(f"    τ1: {fmt_trace(ops1, keys1)}")
      dim(f"    sz1: {sz1}")

      # NEW: show Π totals (so you see “same what”)
      ins0, del0 = totals_per_key(M, ops0, keys0)
      ins1, del1 = totals_per_key(M, ops1, keys1)
      dim(f"    Π totals: ins0={ins0} del0={del0} | ins1={ins1} del1={del1}")

      # Concrete validation per-key counts
      v0, v1 = validate_concrete(M, ops0, keys0), validate_concrete(M, ops1, keys1)

      if v0 is None and v1 is None:
         ok("  CONCRETE-VALID witness ✅ (no per-key negative counts)")
         return True, (ops0, keys0, ops1, keys1), refinements

      # NEW: explain spuriousness + refine earliest violation
      warn("  SPURIOUS witness ❌ (concrete validity failed; abstraction was too weak)")

      if v0 is None:
         tr, (bad_step, bad_key) = 1, v1
      elif v1 is None:
         tr, (bad_step, bad_key) = 0, v0
      else:
         if v0[0] <= v1[0]:
            tr, (bad_step, bad_key) = 0, v0
         else:
            tr, (bad_step, bad_key) = 1, v1

      # NEW: show why it failed (prefix counts)
      ops_bad, keys_bad = (ops0, keys0) if tr == 0 else (ops1, keys1)
      pref = prefix_counts(M, ops_bad, keys_bad, bad_step)
      warn(f"    earliest violation: trace={tr} step={bad_step} key={bad_key}  prefix_counts={pref}")

      # NEW: show simple prefix I/D counts for that key at that step (human view of lemma)
      ins_k = sum(1 for u in range(bad_step+1) if ops_bad[u] == INS and int(keys_bad[u]) == bad_key)
      del_k = sum(1 for u in range(bad_step+1) if ops_bad[u] == DEL and int(keys_bad[u]) == bad_key)
      warn(f"    lemma idea: prefix_ins(key={bad_key}) - prefix_del(key={bad_key}) >= 0  (here {ins_k}-{del_k} >= 0 violated)")

      refinements.append(refine_lemma(op, key, tr, bad_step, bad_key, L))
      warn(f"    added refinement #{len(refinements)}")

   raise RuntimeError("Refinement budget exceeded")

# ================ Outer search of K ================

inf(f"Starting outer search: K from {K_upper} down to 0   (M={M}, L={L})")
for K in range(K_upper, -1, -1):
   sat_ok, w, refinements = find_witness_for_K(M, L, K, refinements)
   if sat_ok:
      bestK = K
      bestW = w
      ok(f"\n[FOUND MAX] K={K} with concrete-valid witness. total_refinements={len(refinements)}")
      break

inf(f"\nParams: M={M}, L={L}, N={N}, K_upper={K_upper}")
inf(f"Refinement lemmas learned: {len(refinements)}")
inf(f"Best K found (concrete-valid): {bestK}")

if bestW is None:
   bad("No witness found even for K=0 (unexpected for this toy)")
   exit(1)

ops0, keys0, ops1, keys1 = bestW

# Pretty trace
out  = [("I" if o == INS else "D", int(k)) for o, k in zip(ops0, keys0)]
out2 = [("I" if o == INS else "D", int(k)) for o, k in zip(ops1, keys1)]
print(C(Fore.MAGENTA, "\nFinal witness:"))
print("Trace 0:", out)
print("Trace 1:", out2)  # FIXED: was printing `out` by mistake

c0 = simulate_cost(ops0, keys0)
c1 = simulate_cost(ops1, keys1)
print(C(Fore.MAGENTA, f"Cost0={c0}, Cost1={c1}, Gap={c0 - c1}"))
