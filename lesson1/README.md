
Scope: We will treat Z3 as a SAT solver by staying entirely inside propositional logic (Boolean).

Goals:

* Set up a Python env for Z3
* Build a small configuration solver as a pet goal
* Learn the minimal Z3 API surface for SAT
* Practice a mental model: formula -> constraints -> (un)sat -> model (witness assignment).

---

Core vocabulary:

In prop SAT, you have Boolean variables $$x_1, ..., x_n$$, and you build a formula $$\varphi$$ from them using familiar connectives from your discrete math class:

* ∧ (AND)
* ∨ (OR)
* ¬ (NEGATE)
* ⇒ (IF)
* ⇔ (IF AND ONLY IF)
* ⊕ (BITWISE SUM)

Typically when we do SAT, we ask:

> Does there exist an assignment $$\sigma : \{x_i\} \implies \{\texttt{false}, \texttt{true}\} such that \sigma \models \phi$$?

It is important to note that $$\text{SAT}(\phi) \equiv \exists \sigma : \sigma \models \varphi $$.

* If SAT, the solver can return a model (a satisfying assignment) as a constructive witness.
* If UNSAT, there isn't an assignment that satisfies all the constraints at the same time.

A common form of SAT solvers internally is CNF (conjunctive normal form), a conjunction of clauses where each clause is a disjunction of literals. We represent it as:

$$ \varphi \text{ in CNF} \;=\; \bigwedge_{j=1}^{m}\left(\,\bigvee_{k=1}^{r_j} \ell_{j,k}\right), \qquad \ell_{j,k}\in\{x_i,\lnot x_i\}. $$

You don't need to convert to CNF to use Z3 most of the time. Instead, we'll write constraints using high-level connectives and Z3 can handle transformations internally.

---

At a high level:

> A solver decides satisfiability (SAT/UNSAT). If SAT, produce a model. If UNSAT, optionally produce diagnostic artifacts including unsat cores, proofs, and interpolants to model failure.

---

SAT vs SMT (why Z3?)

Z3 is a Satisfiability Modulo Theories solver. SMT generalizes SAT by adding typed domains and theoretic constraints (like integers, bit-vectors, arrays, algebraic datatypes, etc.). In SMT, you still have a satisfiability question, but you have them over richer structures than just {false, true}.

$$\textbf{SMT}_T(\varphi) \equiv \exists \mathcal{M}\in T . \mathcal{M} \models \varphi$$

We'll first model Z3 in the special case where all sorts are Boolean, so the engine behaves like a SAT solver. The reason to start here is more methodological than anything: the workflow is identical when you later add integer arithmetic, bit-vector cost models, and array/state modeling.

The discipline is to represent your problem as constraints, let the solver search values over the constraints, interpret the results, and refine your encoding.

---

Instructions to set up the environment are simple:

```bash
python3 -m venv z3env
source z3env/bin/activate
python -m pip install --upgrade pip
pip install z3-solver
```

Check if you got it: ```python -c "import z3"```.

---

Basic Z3 terminology:

* ```Bool("x")``` creates a Boolean variable symbol $$x$$.
* ```And(...), Or(...), Not(...), Implies(a,b), Xor(a,b)``` build formulas.
* ```Solver()``` creates a constraint storage plus a search engine.
* ```s.add(constraint)``` asserts constraints into your ```s:=Solver()```.
* ```s.check()``` returns ```sat```, ```unsat```, or ```unknown```.
* If ```sat```, then ```s.model()``` returns a model mapping some variables to truth values.

> A model may be partial when some variables are unconstrained (you don't care), and Z3 may omit them or assign an arbitrary value to it when you evaluate successfully.

---

Homework: build a tiny configuration solver


