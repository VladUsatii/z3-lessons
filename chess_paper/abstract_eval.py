
from __future__ import annotations

import chess_rules as R
from abstract_groups import D_ORDER, F_ORDER, K_ORDER, M_ORDER, X_ORDER, score_side_groups

OBJECTIVE_ORDER = (
    "losing",
    "unstable",
    "neutral",
    "pressure",
    "tactical-gain",
    "terminal",
)


def _idx(order, value):
    return order.index(value)


def _forcing_signed(ast):
    f = _idx(F_ORDER, ast.forcing.level)
    return f if ast.stm == ast.focus_color else -f


def objective_score(ast):
    return score_side_groups(ast.opponent) - score_side_groups(ast.focus) + 0.8 * _forcing_signed(ast)


def evaluate_objective(ast, cfg=R.RulesConfig()):
    board = R.board_from_fen(ast.fen)

    if board.is_checkmate():
        return "losing" if ast.stm == ast.focus_color else "terminal"

    focus_k = _idx(K_ORDER, ast.focus.K)
    opp_k = _idx(K_ORDER, ast.opponent.K)
    focus_d = _idx(D_ORDER, ast.focus.D)
    opp_d = _idx(D_ORDER, ast.opponent.D)
    focus_m = _idx(M_ORDER, ast.focus.M)
    opp_m = _idx(M_ORDER, ast.opponent.M)
    focus_x = _idx(X_ORDER, ast.focus.X)
    delta = objective_score(ast)
    forcing = _idx(F_ORDER, ast.forcing.level)

    if focus_k >= 3 or (focus_m >= 3 and ast.stm != ast.focus_color):
        return "losing"

    if opp_k >= 3 or opp_m >= 3 or (opp_d >= 3 and forcing >= 2 and ast.stm == ast.focus_color):
        return "tactical-gain"

    if delta <= -4 or (focus_d >= 3 and focus_x >= 2):
        return "losing"
    if delta <= -1 or focus_k > opp_k:
        return "unstable"
    if delta >= 4 or (forcing >= 2 and ast.stm == ast.focus_color):
        return "tactical-gain"
    if delta >= 1 or (forcing >= 1 and ast.stm == ast.focus_color):
        return "pressure"
    return "neutral"


def objective_index(value):
    return OBJECTIVE_ORDER.index(value)


def compare_objectives(a, b):
    ia = objective_index(a)
    ib = objective_index(b)
    if ia < ib:
        return -1
    if ia > ib:
        return 1
    return 0
