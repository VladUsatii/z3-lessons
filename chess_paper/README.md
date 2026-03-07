# Z3 Chess

## Purpose

This document defines the first abstract domain for a bounded adversarial chess reasoner. The goal is not to solve chess and not to imitate a conventional engine evaluation function. The goal is to define a compressed state space in which bounded-horizon adversarial reasoning is substantially cheaper than naive concrete search while still being anchored to exact chess semantics through validation and counterexample-guided refinement.

The system is intended to operate over a trusted concrete semantics layer:

* legal move generation
* move application
* terminal predicates
* certificate replay / validation

The abstract domain defined here is the object optimized by the prover. The concrete semantics are used only to validate or refute abstractly chosen moves and strategies.

---

## 1. Concrete game model

Let a concrete state be

`s = (B, stm, r)`

where:

* `B` is the board configuration
* `stm ∈ {w, b}` is side to move
* `r` is the rules configuration for the current micro-chess fragment

For the first implementation, the rules fragment excludes castling, en passant, repetition, and the 50-move rule unless explicitly enabled. Promotions may be allowed.

Let:

* `Moves(s)` be the set of legal moves in state `s`
* `step(s, m)` be the successor state produced by legal move `m`
* `terminal(s)` indicate checkmate or other chosen terminal conditions

We assume the concrete semantics are exact and are the sole trusted source of truth about legality and transition.

---

## 2. Problem solved by the abstract domain

Given:

* a root state `s0`
* a bounded horizon `H`
* an objective lattice `L`

we want to compute a move or bounded strategy that maximizes the strongest objective level in `L` that can survive adversarial play within horizon `H`.

The abstract domain supports a bounded optimization problem of the form

`V_H^(#)(a) = Opt_H( A(s0) )`

where:

* `A : S -> S#` maps concrete states to abstract states
* `S#` is the abstract state space
* `Opt_H` is a bounded adversarial optimization operator defined over abstract states

The concrete checker then determines whether the abstractly chosen move or strategy is sound with respect to exact concrete play.

---

## 3. Design principles for the abstract domain

The domain is designed under five constraints.

First, it must be relational. Independent scalar features are not sufficient because many tactically decisive positions are controlled by coupled state changes rather than by one variable.

Second, it must be local enough to update efficiently under moves. If every move forces recomputation of the entire abstract state from scratch, the abstraction has failed as a compression mechanism.

Third, it must be adversarially meaningful. The groups must preserve the structures that affect bounded best-response play, not merely static desirability.

Fourth, it must support refinement. When a concrete counterexample invalidates an abstract best move, the abstract state must be splittable or strengthenable in a targeted way.

Fifth, it must remain external to the trusted concrete semantics. The abstract domain may guide reasoning, but it must never become the sole arbiter of correctness.

---

## 4. Abstract state overview

The abstract state is a tuple of grouped tactical relations:

`A(s) = (K, F, D, X, M, R, T)`

where:

* `K` = king-shell integrity and exposure state
* `F` = forcing pressure state
* `D` = defender overload / dependency state
* `X` = line fragility state
* `M` = material instability state
* `R` = race / promotion pressure state
* `T` = tempo / initiative persistence state

Not all groups must be active in the first implementation. A minimal first implementation may use

`A0(s) = (K, F, D, X, M)`

and add `R` and `T` later.

The key point is that each coordinate is itself a grouped relational summary, not a single number.

---

## 5. Co-use groups and multi-variable state tracking

The central modeling move is to define groups not by theme alone, but by co-use.

Let `P = {p1, ..., pn}` be a family of concrete predicates or measurements over states and move transitions. Examples include:

* whether a king shell square is occupied or controlled
* whether a defender simultaneously covers multiple critical obligations
* whether a line piece has a latent discovered attack path
* whether a key square is multiply attacked and under-defended
* whether a pawn race is one tempo from promotion

Define a co-use relation `~` over these predicates:

`pi ~ pj` iff one or more of the following hold consistently across the target tactic class:

* they are jointly read in deciding whether a bounded tactical motif exists
* they are jointly changed by the same move families
* they are jointly implicated in the same concrete counterexample traces
* they repeatedly participate in the same dependency chain during refinement

A co-use group is then an equivalence class or clustered subset induced by `~`, possibly after thresholding or graph clustering.

This means the abstract coordinates are not arbitrary feature bundles. They are intended to reflect true interaction structure in bounded tactical reasoning.

---

## 6. Detailed definition of each group

### 6.1 King-shell integrity group `K`

`K` summarizes how vulnerable the king is under bounded forcing play.

It should not merely record whether the king is in check. It should capture shell stability. A useful first categorical state is:

`K ∈ {safe, pressured, fractured, critical}`

Possible contributors:

* number and type of attacked shell squares
* availability and safety of escape squares
* openness of adjacent files / diagonals
* presence of defending pieces in the shell
* forcing-move access by the attacker

A simple first rule set:

* `safe`: no immediate forcing route and shell structure intact
* `pressured`: checks or forcing access exist but shell still defends
* `fractured`: shell coverage compromised or escape geometry unstable
* `critical`: bounded forcing continuation threatens terminal collapse

This group is inherently multi-variable because shell stability depends on occupancy, attack relations, mobility, and defending assignments together.

### 6.2 Forcing pressure group `F`

`F` captures whether the side to move can compel narrow reply sets.

Suggested categorical state:

`F ∈ {none, latent, forcing, forcing+}`

Contributors:

* legal checks available
* forcing captures available
* threats whose refutation set is small
* sequences where the opponent's admissible safe replies are sharply reduced

This group matters because bounded tactical play is often dominated by forcing sequences, and these are exactly the places where shallow but well-targeted reasoning can outperform broad but unfocused search.

### 6.3 Defender dependency group `D`

`D` models overload, multi-obligation defense, and fragile support assignments.

Suggested state:

`D ∈ {stable, shared-load, overloaded, collapsing}`

Contributors:

* a defender covering multiple tactically critical items
* pieces whose removal or diversion breaks several safety conditions at once
* local under-defense relative to attack concentration
* brittle defensive chains

This is perhaps the clearest chess analogue of multi-variable inconsistency. Individually, each defended item may appear acceptable; jointly, the defensive structure may be impossible to sustain after one forcing move.

### 6.4 Line fragility group `X`

`X` tracks whether important tactical lines are rigid, latent, or one move away from tactical activation.

Suggested state:

`X ∈ {closed, latent, active, explosive}`

Contributors:

* pins, skewers, x-rays, battery structures
* discovered attack possibilities
* obstructions whose removal changes attack geometry
* aligned king / queen / rook / bishop relations

This group reflects that one move often changes the tactical meaning of several variables simultaneously by opening a line.

### 6.5 Material instability group `M`

`M` does not track static material count. It tracks whether the local material configuration is stable under forcing continuation.

Suggested state:

`M ∈ {stable, contestable, volatile, winning-sequence}`

Contributors:

* hanging pieces
* tactical exchange chains
* forced recapture structures
* local imbalance where forcing play can realize gain

Material instability is important because many strong moves are not immediately winning materially but create a bounded tactical instability that the opponent cannot fully neutralize.

### 6.6 Race / promotion pressure group `R`

`R` is optional in the first implementation but should be part of the long-term domain.

Suggested state:

`R ∈ {none, latent-race, active-race, promotion-critical}`

Contributors:

* passed pawns
* mutual promotion tempos
* blockade fragility
* forcing interactions around promotion squares

### 6.7 Tempo / initiative persistence group `T`

`T` summarizes whether a side can sustain initiative over several plies or whether the initiative is likely to dissipate.

Suggested state:

`T ∈ {neutral, initiative, sustained-initiative, forced-sequence}`

Contributors:

* repeated forcing access
* move urgency asymmetry
* inability of opponent to safely improve position
* tactical tempo gains

This group is useful because many human judgments of a move's "potential damage" are actually judgments about whether initiative will persist over a short horizon.

---

## 7. Abstract objective lattice

The abstract solver should not optimize a floating-point score initially. It should optimize over a small lattice of bounded-horizon outcomes.

A first objective lattice `L0` can be:

`losing < unstable < neutral < pressure < tactical-gain < terminal`

where:

* `losing` means bounded concrete validation found an adversarial collapse
* `unstable` means the position cannot currently be certified and is tactically fragile
* `neutral` means no certified bounded-horizon gain
* `pressure` means bounded forcing / initiative improvement is sustained
* `tactical-gain` means bounded material or structural gain is forced
* `terminal` means forced mate or equivalent terminal win within the horizon

The exact ordering and names can be revised, but the principle matters: the solver should optimize over a discrete, explainable value structure that supports refinement and validation.

---

## 8. Abstract transformers

Each legal move `m` in concrete state `s` induces an abstract transformer:

`T#( A(s), m ) = A( step(s, m) )`

The simplest first implementation computes abstract successors by concrete replay followed by abstraction. That is:

1. compute `s' = step(s, m)` using exact semantics
2. compute `A(s')`

This is correct and easy to validate, although it does not yet exploit symbolic algebra internally.

A more advanced implementation replaces recomputation with incremental grouped updates. For that, each move family must carry a cone-of-influence summary specifying which groups may change.

For example:

* checks primarily affect `K`, `F`, `T`
* forcing captures may affect `D`, `M`, `X`, sometimes `K`
* line-opening moves affect `X`, `K`, `D`
* quiet consolidation moves may affect `D` and `T`

Then only affected groups are recomputed or strengthened. This is where co-use tracking becomes computationally valuable.

---

## 9. Bounded adversarial optimization operator

Let `Val_H#(a, stm)` denote the best bounded value at abstract state `a` with side `stm` to move and horizon `H`.

At a conceptual level:

`Val_0#(a, stm) = Eval#(a)`

and for `H > 0`:

`Val_H#(a, stm) = sup_m inf_r Val_{H-1}#( T#(a, m), opp(stm) )`

for the maximizing side, and dually for the minimizing side.

The implementation need not literally use this notation, but the operator should be understood as bounded adversarial optimization over abstract states.

The point of the abstract domain is that `Val_H#` should be far cheaper to compute than the corresponding concrete bounded minimax value while remaining predictive enough to guide concrete validation.

---

## 10. Validation and refutation

A move chosen as abstractly optimal is not automatically accepted.

Given a candidate move `m*`, the validator checks whether the concrete successor state supports the bounded claim that the solver assigned to it.

There are two possible outcomes.

1. The claim survives concrete adversarial validation.
   Then the system can emit a validated strategy or move claim.

2. A concrete counterexample trace is found.
   Then the abstraction was too coarse, and refinement is required.

This means the system remains sound even if the abstract domain is optimistic, because optimism is never trusted without exact replay.

---

## 11. Refinement rules

Refinement must be local, justified, and finite-horizon aware.

Three classes of refinement should be allowed.

### 11.1 Group splitting

If a counterexample shows that one abstract category conflates tactically distinct states, split that category.

Example:

* `K = pressured` may need to split into

  * `pressured-with-safe-escape`
  * `pressured-with-unsafe-escape`

### 11.2 Transformer strengthening

If a move family summary was too permissive, refine the transformer so that it distinguishes more cases.

Example:

* line-opening moves may need separate cases depending on whether the opened line targets king shell or only material.

### 11.3 Objective refinement

If two abstractly equivalent states differ in concrete bounded outcome because the objective lattice is too coarse, refine the lattice or the mapping into it.

Example:

* `pressure` may need to split into

  * `pressure-reversible`
  * `pressure-sustained`

Refinement should always be triggered by a concrete counterexample, never by arbitrary complexity inflation.

---

## 12. First implementable instantiation

The first implementation should be deliberately narrow.

### Concrete scope

* micro-chess fragment
* horizon `H` small, e.g. 4 to 8 plies
* exact legality from trusted oracle

### Abstract domain scope

Use only:

* `K`
* `F`
* `D`
* `X`
* `M`

### Objective lattice

Use:

* `losing`
* `unstable`
* `neutral`
* `pressure`
* `tactical-gain`
* `terminal`

### Initial transformer implementation

Use exact replay plus abstraction recomputation:

`T#( A(s), m ) := A( step(s, m) )`

This is less elegant than a fully symbolic transformer library, but it gives a correct and testable first system.

---

## 13. Program structure implied by this document

The codebase should eventually have the following conceptual layers.

### Exact semantics layer

Already mostly present:

* FEN normalization
* legality
* move application
* terminal predicates
* certificate checker

### Abstract domain layer

To be built:

* `abstract_state.py`
* `abstract_groups.py`
* `abstract_eval.py`
* `abstract_transform.py`

### Abstract game solver

To be built:

* bounded adversarial optimization over abstract states
* first version may be implemented directly in Python
* later version may be encoded into SMT / QBF / mixed CEGAR backend

### Concrete validator / refuter

To be built:

* check whether abstractly chosen move survives exact play
* if not, produce a counterexample trace

### Refinement engine

To be built:

* map counterexample to failed group or transformer assumptions
* apply one of the allowed refinement rules

---

## 14. Evaluation questions

This domain exists to answer specific empirical questions.

1. Does the abstractly chosen move align with stronger bounded concrete search more often than cheap scalar heuristics?
2. How many concrete refutations are needed before the abstractly best move stabilizes?
3. Which groups contribute most to predictive power?
4. Which groups are most frequently refined?
5. Does co-use grouping outperform ordinary independent feature sets under the same bounded-horizon budget?