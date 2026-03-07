Goal: Encode and solve the problem $$\exists \tau_0,\tau_1.\;\; \underbrace{\textsf{Valid}(\tau_0)\land \textsf{Valid}(\tau_1)}_{\text{validator}} \;\land\; \underbrace{\Pi(\tau_0)=\Pi(\tau_1)}_{\text{projection / comparability}} \;\land\; \underbrace{\textsf{Cost}(\tau_0)-\textsf{Cost}(\tau_1)\ge K}_{\text{gap objective}}$$.

You'll build a minimal CEGAR skeleton that is actively useful in countless research avenues:

1. Solve an abstraction Valid (coarse semantics).
2. Extract a witness (two traces).
3. Validate against the concrete semantics (```validate()``` in Python)
4. If spurious, add a refinement lemma derived from the counterexample and re-solve.

---

What a single trace claim can prove and why it is weak

A single-trace AC-DoS style query is typically:

$$ \exists x \textsf{Valid}(x) \land \textsf{Cost}(x) \ge K $$.

This finds some valid input that makes the program do $$\ge K$$ work.

Problem: this is almost always true if you have a large enough $$x$$ unless you normalize. You'll rediscover big requests cost more, which is an obvious finding, or that bigger blocks should cost more, or even that more transactions cost more, which is not a vulnerability in and of itself. It is actually just expected scaling with some time. Even if you added a size bound into the mix:

$$ \exists x \textsf{Valid}(x) \land \textsf{Size}(x) \le S \land \textsf{Cost}(x) \ge K $$.

It still mixes two failure modes together, namely: real amplification (worst-case scenario of some algorithm) with legitimate work (the system is doing more meaningful work within the bound with a higher input).

Single-trace encodings are therefore high false-positives unless you already had a near-perfect semantic validity and normalization system that matches the intent of comparing two traces. Again, it might be better to just introduce a slow AND fast trace to see their difference in cost.

---

What does a two trace claim prove and why it matches the frontier/SOTA of AC-DoS

In my specific research direction, we're looking for two inputs, one average and one worst, that can yield significant structural gaps in algorithmic time complexity.

Two traces can encode a differential statement, like:

$$\exists x_0, x_1 \; \tesxtsf{Valid}(x_0) \land \textsf{Valid}(x_1) \land \Pi(x_0)=\Pi(x_1)\land \textsf{Size}(x_0)\approx \textsf{Size}(x_1)\land \textsf{Cost}(x_0)-\textsf{Cost}(x_1)\ge K $$

* Both $$x_0$$ and $$x_1$$ are valid.
* They are comparable by construction, so they have the same observable outcome under some project $$\Pi$$ (same externally relevant result) and similar size/shape.
* Yet one of them is strictly (and perhaps substantially) more expensive by some $$\ge K$$.
* $$\Pi$$ is the formal outcome relation. In Ethereum clients, for example, this might be (a) the same accepted/rejected final decision, (b) the same final state root or receipts root, (c) same mempool contents modulo reordering, (d) same admitted transactions set, and even (e) the same result of block validity after some algorithm. If you can't keep $$\Pi$$ fixed, you're often paying for different outcomes, which is impossible to objectively interpet downstream. It is crucial to avoid comparing different outcomes when possible.

--

WCS vs. the baseline is two-trace by definition

* Same input size $$n$$
* Two varying inputs $$x_{avg}$$ and $$x_{worst}$$
* Cost differs dramatically

The classic example given is Quicksort:

* $$x_1$$: random permutation is $$O(n \log(n))$$
* $$x_0$$: sorted input with bad pivot rule $$O(n^2)$$

Same $$n$$, different inherent cost. In protocol settings, you also need the same outcome under $$\Pi$$ because protocols have validity constraints and observable downstream effects.

An attacker needs to remain within the validity rules, keep the externally visible effect acceptable/unchanged, and force nodes into an expensive path, and there is no way to do it without keeping a stable baseline comparison $$x_1$$.

Two traces aren't necessary if you can define a robust scalar normalizer and prove that $$\exists x. textsf{Valid}(x)\land \textsf{Cost}(x)\ge f(\textsf{Size}(x))\cdot g(\textsf{Size}(x))$$ with a meaningful baseline $$f$$ and a superlinear factor $$g$$. In real clients, however, the baseline is very hard to specify without reintroducing some notion of $$\Pi$$ with comparability constraints. The two-trace idea is implicit, but there are extra steps involved without using it from jump.

---

Challenge: Implement a basic CEGAR toy with a two-trace gap. This has *direct* applications to various research avenues.
