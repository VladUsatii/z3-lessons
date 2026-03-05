# Chess fun in Z3

Learning Z3 by building a chess solver.

### How it looks for now

* Input: FEN + bound k plies (k/2 per side)
* Claim: Side to move has a forced checkmate in <= k plies
* Certificate: a strategy tree/DAG that (a) picks a move for the prover side at each of its tunrs and covers (b) all legal opponent replies at opponent turns ending in checkmate within the bound. Can also be run boundless, but path explosion is a main hurdle here.
* Ruleset: orthodox legality excluding castling and en-passant for now. Ignore repetition and 50-move.

### What a certificate wil look like

```json
{
   "version": 1,
   "root_fen": "...",
   "k_plies": 5,
   "nodes": {
      "H(root)": {
         "fen": "...",
         "turn": "P",               // P: prover side, O: opponent side
         "ply": 0,
         "move": "e2e4",            // required if P
         "children": {              // required if O
            "g8f6": "H(child1)",
            "d7d5": "H(child2")
         }
      },
      "H(child1)": { "..." : "..." }
   }
}
```

* ```H(*)``` is any stable node id (hash of the FEN and the ply).
* On prover nodes: exactly 1 chosen move.
* On opponent nodes: you must enumerate all the legal replies (after filtering for the forbidden move types) with each mapping to a child node

The checker behavior is pretty straightforward:

```check(cert)```:

1. For every node: fen parses, turn matches side-to-move from fen, and ply is consistent with the parent
2. Prover node: move is legal in fen, apply it -> child exists
3. Opponent node: children keys are exactly the set of legal moves from fen (after the filters)
4. Leaf condition: whenever ply == k_plies, the state must already be checkmate for the side-to-move's opponent or you can allow an earlier mate if you want.
5. No illegal-move cheating by the opponent is possible because we enumerate the legal children in the actual checker supplied by ```python-chess```.

### Generating certificates without SMT as a baseline

Before any Z3 is introduced, we write a tiny bounded mate prover that searches and emits certificates so we can test the checker end-to-end.

```prove_naive(fen, k)```:

* If prover-to-move: exists a move such that for all opponent replies the remainder is provable
* If opponent-to-move: for all replies, remainder is provable
* Even if just for the last 1-4 moves of a game, it still validates that we have the right semantics, schema, and checker.
* We can even have a fallback to a full "played" game so as to match our moves to it.


