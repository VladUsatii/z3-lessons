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


