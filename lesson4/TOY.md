How does the toy work?

You have two traces. For each trace:

* it starts from the same initial state
* must satisfy the same grammars
* must satisfy legality constraints like $$size_t \geq 0$$
* ends in the same comparable final condition, which is $$size_{0,L} = size_{1,L} = 0$$ and matching per-key totals across traces here.

There are two running quantities per trace:

1. State: what evolves step-by-step like $$size_{t+1} = size_{t} + \delta_t$$ where $$\delta_t$$ is $$+1$$ for ```INS``` and $$-1$$ for ```DEL```. This is what constraints like $$size_t \geq 0$$ apply to.
2. Accumulation: at every step, we define a step cost $$c_t$$ that is $$1$$ if $$\texttt{INS}$$ and $$sizee_t$$ if $$\texttt{DEL}$$. The total cost is then $$\C = \sum_{t=0}^{L-1} c_t$$, which is the **sum** we want to maximize the gap of.

* $$size_t$$ is the evolving state
* $$C$$ is the accumulated total cost
* we aren't maximizing the final state
* we maximize the difference in accumulated cost **totals**.

---

The actual objective is clear from these two side-by-side traces:

Find valid, constrained, and comparable traces $$\tau_0$$ and $$\tau_1$$ such that $$C(\tau_0) - C(\tau_1)$$ is maximized. It is an optimization problem.

SMT solvers are easiest to use in decision form, so instead of directly asking to find the maximal gap in the traces total costs, we ask if there is a witness whose gap is at least $$K$$.

That is, $$\exists \tau_0, \tau_1 . \text{Valid}(\tau_0) \wedge \text{Valid}(\tau_1) \wedge \Pi(\tau_0) = \Pi(\tau_1) \wedge C(\tau_0) - C(\tau_1) \ge K$$, which is the correct format for a SAT question:

* SAT if the gap $$\ge K$$ is achievable
* UNSAT else.

---

The hidden abstraction is that because the moving parts were monotone, it was all just binary search "by hand."

If a gap of $$K$$ is achievable, then any smaller gap $$K' \le K$$ can be achieved as well under that witness.

So the predicate is actually just $$F(K) =$$ there exists a valid comparable pair with gap $$\ge K$$ -- the shape of binary search by hand.

---

What is CEGAR doing here?

CEGAR is *counterexample-guided abstraction refinement* and the workflow is natively:

1. Solve an abstraction of an actual problem.
2. If the solver says UNSAT, you are done for that abstraction level.
3. If the solver returns a witness, check whether it is real.
4. If it is real, you're finished.
5. If it isn't real, you have to extract the constraints by which it failed and add a new constraint that blocks that class of fake witnesses from re-appearing downstream.
6. Solve again.

The iterative loop continues until either a real witness appears or the problem becomes UNSAT (at the sight of path explosion, this is probably the case).

---

CEGAR pseudocode:

```
function CEGAR():
   A := initial_abstraction()

   while true:
      result, witness := solve(A)

      if result == UNSAT: return UNSAT
      if validate_concretely(witness): return SAT, witness

      cex_info := explain_spuriousness(witness)
      lemma := refine(cex_info)
      A := A and lemma
```

In a two-trace gap setting, things differ a tiny bit because the decision query for a fixed threshold $$K$$ is:

$$\exists\tau_0, \tau_1. \text{AbstractValid}(\tau_0) \land \text{AbstractValid}(\tau_1) \land \Pi(\tau_0)=\Pi(\tau_1) \land C(\tau_0)-C(\tau_1)\geq K$$

That means the CEGAR loop is:

```
function feasible(K):
   A := base_abstract_encoding()

   while true:
      result, (t0, t1) := solve(A and [C(t0)-C(t1) >= K])

      if result is UNSAT, return False
      if concrete_validate(t0) and concrete_validate(t1): return true, (t0, t1)

      v := earliest concrete violation in t0 or t1
      lemma := refinement_from(v)
      A := A and lemma
```

The genuine magic in our toy comes from how ```refinement_from(v)``` is coded (prepare to be mind-blown):

If you have a trace failure $$(tr, t, k)$$, the refinement lemma is created as ```|INS_k[0..t]| - |DEL_k[0..t]| >= 0```.

This is added back into the solver so our next abstract witness can't make the same mistake.

Concretely, this is what the actual loop in our toy is:

```
A := size_only abstraction

while true:
   result, witness := solve(A and [gap >= K])

   if result == UNSAT, return false
   if witness is concrete-valid, return true, witness

   (tr, t, k) := earliest prefix where key k breaks bound >= 0
   A := A and [prefix_ins(tr,k,t) - prefix_del(tr,k,t) >= 0]
```

Every fake witness helps you add a new semantic layer and constrain meaning autonomously.



