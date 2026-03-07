
from __future__ import annotations

from dataclasses import dataclass

import chess_rules as R
from abstract_eval import compare_objectives, evaluate_objective, objective_score
from abstract_state import AbstractState


@dataclass(frozen=True)
class SearchResult:
    move: str | None
    objective: str
    score: float
    pv: tuple[str, ...]
    leaf: AbstractState

    def to_dict(self):
        return {
            "move": self.move,
            "objective": self.objective,
            "score": self.score,
            "pv": list(self.pv),
            "leaf": self.leaf.to_dict(),
        }


def _better_max(lhs, rhs):
    c = compare_objectives(lhs.objective, rhs.objective)
    if c != 0:
        return c > 0
    return lhs.score > rhs.score


def _better_min(lhs, rhs):
    c = compare_objectives(lhs.objective, rhs.objective)
    if c != 0:
        return c < 0
    return lhs.score < rhs.score


def _terminal_or_leaf(ast, depth, cfg):
    if depth <= 0:
        return True
    if R.is_terminal(ast.fen):
        return True
    if not R.legal_moves(ast.fen, cfg):
        return True
    return False


def bounded_abstract_search(fen, depth, cfg=R.RulesConfig(), focus_color=None):
    root = AbstractState.from_fen(fen, cfg=cfg, focus_color=focus_color)
    return _search(root, depth, cfg)


def _search(ast, depth, cfg):
    if _terminal_or_leaf(ast, depth, cfg):
        obj = evaluate_objective(ast, cfg)
        return SearchResult(None, obj, objective_score(ast), (), ast)

    legal = R.legal_moves(ast.fen, cfg)
    maximizing = ast.stm == ast.focus_color
    best = None

    for mv in legal:
        next_fen = R.apply_move(ast.fen, mv, cfg)
        child = AbstractState.from_fen(next_fen, cfg=cfg, focus_color=ast.focus_color)
        sub = _search(child, depth - 1, cfg)
        cur = SearchResult(mv, sub.objective, sub.score, (mv,) + sub.pv, sub.leaf)

        if best is None:
            best = cur
            continue
        if maximizing and _better_max(cur, best):
            best = cur
        if not maximizing and _better_min(cur, best):
            best = cur

    return best
