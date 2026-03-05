Goal: Introduce the three SMT theories that are most useful in program analysis. Also, we'll look at the first scalable pattern for exploring multiple models. Hint: enumeration by blocking clauses.

---

Integers vs. Bit-vectors

What is the difference?

* Integers lie on $$\mathbb{Z}$$.
* Operations are unbounded (no overflow).
* Constraints like ```x >= 0``` and ```x + y == 10``` are in integer arithmetic.

* Bit-vectors are represented as ```BitVec(w)```.
* The domain is fixed with words: $$\{0, ..., 2^{w} - 1\}$$.
* Arithmetic is now modulo $$2^{w}$$ (overflow wraps).
* Comparisons come in two different flavors: unsigned (```UGE```, ``ULT```, etc.) and signed (```x < y``` uses signed for bit-vectors in Z3).

When working within Ethereum (like I am), we almost always need bit-vectors when modeling

* machine integers (like 64-bit counters)
* hashes/packed fields
* overflow/underflow-sensitive logic

For cost models and counts, you can use integers because overflow is something we don't want to worry about, unless we precisely target a bug regarding overflow.

---

Arrays

Z3 array sort ```Array(K,V)``` models a total map $$K \to V$$ with

* ```Select(A, k)``` = value at key k
* ```Store(A, k, v)``` = new array equal to A except at k mapped to v

This allows us to functionally/persistently model:

* maps from nonce to fee, slot to count, index to state,
* heap abstractions
* sparse state without explicit simulation
* and each ```Store``` returns a new array term.

---

Uninterpreted Functions (UFs)

A UF is a function symbol that has no built-in meaning other than congruence.

So $$\text{if} x = y \text{then} f(x) = f(y)$$, which is useful when you want

* to represent some function computed by code but don't want to encode its internals yet
* abstraction layers for CEGAR: start with UFs, refine only when you need to

---

Enumeration

Given a SAT formula, you often want multiple witnesses, or all distinct solutions over a subset of variables, or to sample solution space.

The pattern is:

1. ```check()```
2. Read model $$m$$
3. Build a blocking clause that excludes exactly that assignment on chosen variables
4. ```add(block)``` and repeat.

For Boolean variables $$x_1, ..., x_k$$, if the model assigns $$x_i = v_i$$, block with:

$$\bigvee_{i=1}^{k} (x_i \ne v_i)$$.

This guarantees that the next model differs on at least one of the chosen variables.

---

Challenge: Work with UFs
