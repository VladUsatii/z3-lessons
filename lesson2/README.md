Objective:

* Introduce incremental solving via ```push()``` and ```pop()``` to explore a family of related constraint systems without rebuilding the solver's state.
* Demonstrating assumptions and UNSAT cores so you can toggle requirements cheaply and extract diagnostics when things fail.
* Introducing integers (SMT) by leaving pure prop SAT and adding integer theory (quantifier-free integer arithmetic) while preserving the same engineering discipline: encode -> check -> interpret -> refine.

---

Incremental solving and why it matters

A ```Solver()``` maintains a base assertion set (all the constraints we permanently add) and a stack of frames created by ```push()```.

* ```s.add(φ)``` adds constraint φ into the current top frame.
* ```s.push()``` creates a new frame on top of the stack (empty by default)
* ```s.pop()``` discards the top frame (and all the constraints added since the matching ```push()```.

If the base constraints are $$B$$, and frames contain $$F_1, F_2, ..., F_k$$, then ```check()``` solves $$B \land \bigwedge_{i=1}^{k} F_i$$. This matters at scale because:

* you rarely solve only one constraint system -- often many slight variants with different goals, templates, bounds, invariants, candidate traces, and even "K"'s in a gap constant.
* rebuilding the solver repeatedly is wasteful -- you even lose learned lemmas and internal state that makes repeated checks faster
* push/pop gives you the standard loop form used in CEGAR: assert the candidate abstraction -> check -> if SAT but spurious, pop and refine -> re-check.

---

Z3 supports checking SAT under a list of assumption literals $$a_1, ..., a_t$$, where each $$a_i$$ is a Boolean. You do this by calling ```s.check(a1, a2, ..., at)```.

* This asks whether the current asserted constraints are SAT together with those literals set to true.
* $$\text{check}(a_1,\dots,a_t) \equiv \text{SAT}\Big(B \land \bigwedge F_i \land \bigwedge_{j=1}^{t} a_j\Big)$$
* You don't assert the requirement directly, but rather gate it: add ```Implies(reqX, constraintX)``` permanently and then toggle it by passing ```reqX``` as an assumption at check-time.

Assumptions basically become feature flags for constraint groups.

---

A minimal explanation of inconsistency (UNSAT cores)

When ```check(...)``` return ```unsat```, you want to know which set of requirements caused that contradiction to happen. There are really two common patterns for this in Z3:

* Assumption-core. If you pass assumption literals to ```check(...)```, then ```s.unsat_core()``` returns a subset of those assumptions that is already inconsistent with the permanent assertions.
* Tracked assertions. You can tag constraints with Boolean names and ask Z3 for a core of tracked constraints.

With assumption-core, you are only looking over assumptions. It is not guaranteed minimum, but typically small and actionable. It is an excellent choice for which toggles broke your system. With tracked assertions (```assert_and_track```), the core can include base constraints too (if tracked). It is useful for debugging large encodings where the issue is not just a set of toggles. And there is slightly more bookkeeping involved, but it scales rather well compared to Assumption-core.

---

Integers.

In SAT, every variable ranges over the set {false, true}. In SMT over *integers*, you have to introduce variables over $$\mathbb{Z}$$ with arithmetic constraints. Here are a few examples so this isn't hand-wavey:

* ```n = Int("n")``` creates an integer symbol $$n \in \mathbb{Z}$$.
* You can assert constraints like ```n >= 0```, ```n + m == S```, and so on.
* This jump matters because our target applications of SAT/SMT are almost never just boolean satisfiability.
* We can now encode things like size symbols $$n, m, ...$$, bounds $$0 \leq n \leq N$$, relationships $$n + m = S$$, linear cost expressions $$c = \alpha n + \beta m + \psi$$, and even gap constraints $$c_{\text{slow}} - c_{\text{fast}} \geq K$$.

This is like 90% of the mechanical pre-requisites for template-based gap solving.

---

Challenge: incremental solving, assumptions/cores, and integers

