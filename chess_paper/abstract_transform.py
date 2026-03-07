
from __future__ import annotations

import chess_rules as R
from abstract_state import AbstractState


def abstract_state_from_fen(fen, cfg=R.RulesConfig(), focus_color=None):
    return AbstractState.from_fen(fen, cfg=cfg, focus_color=focus_color)


def step_abstract(ast, move_uci, cfg=R.RulesConfig()):
    next_fen = R.apply_move(ast.fen, move_uci, cfg)
    return AbstractState.from_fen(next_fen, cfg=cfg, focus_color=ast.focus_color)


def abstract_successors(fen, cfg=R.RulesConfig(), focus_color=None):
    fen = R.normalize_fen(fen)
    out = {}
    for mv in R.legal_moves(fen, cfg):
        next_fen = R.apply_move(fen, mv, cfg)
        out[mv] = AbstractState.from_fen(next_fen, cfg=cfg, focus_color=focus_color)
    return out
