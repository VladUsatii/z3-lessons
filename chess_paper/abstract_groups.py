
from __future__ import annotations

from dataclasses import dataclass

import chess
import chess_rules as R

K_ORDER = ("safe", "pressured", "fractured", "critical")
F_ORDER = ("none", "latent", "forcing", "forcing+")
D_ORDER = ("stable", "shared-load", "overloaded", "collapsing")
X_ORDER = ("closed", "latent", "active", "explosive")
M_ORDER = ("stable", "contestable", "volatile", "winning-sequence")
R_ORDER = ("none", "latent-race", "active-race", "promotion-critical")
T_ORDER = ("neutral", "initiative", "sustained-initiative", "forced-sequence")

PIECE_VALUE = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}


@dataclass(frozen=True)
class SideGroups:
    color: str
    K: str
    D: str
    X: str
    M: str
    R: str = "none"
    T: str = "neutral"

    def to_dict(self):
        return {
            "color": self.color,
            "K": self.K,
            "D": self.D,
            "X": self.X,
            "M": self.M,
            "R": self.R,
            "T": self.T,
        }


@dataclass(frozen=True)
class ForcingSummary:
    level: str
    checking_moves: int
    forcing_moves: int
    best_reply_width: int

    def to_dict(self):
        return {
            "level": self.level,
            "checking_moves": self.checking_moves,
            "forcing_moves": self.forcing_moves,
            "best_reply_width": self.best_reply_width,
        }


OTHER = {chess.WHITE: chess.BLACK, chess.BLACK: chess.WHITE}


def _rank_index(value, order):
    return order.index(value)


def _color_bool(color):
    if color in ("w", chess.WHITE):
        return chess.WHITE
    if color in ("b", chess.BLACK):
        return chess.BLACK
    raise ValueError(f"bad color: {color!r}")


def _color_str(color):
    return "w" if _color_bool(color) == chess.WHITE else "b"


def _legal_moves_filtered(board, cfg):
    return list(R.filter_moves(board, board.legal_moves, cfg))


def _king_zone(board, color):
    ksq = board.king(color)
    if ksq is None:
        return set()
    out = {ksq}
    kf = chess.square_file(ksq)
    kr = chess.square_rank(ksq)
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if df == 0 and dr == 0:
                continue
            nf = kf + df
            nr = kr + dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                out.add(chess.square(nf, nr))
    step = 1 if color == chess.WHITE else -1
    for df in (-1, 0, 1):
        nf = kf + df
        nr = kr + step
        if 0 <= nf < 8 and 0 <= nr < 8:
            out.add(chess.square(nf, nr))
    return out


def _safe_king_exits(board, color):
    ksq = board.king(color)
    if ksq is None:
        return 0
    enemy = OTHER[color]
    count = 0
    kf = chess.square_file(ksq)
    kr = chess.square_rank(ksq)
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if df == 0 and dr == 0:
                continue
            nf = kf + df
            nr = kr + dr
            if not (0 <= nf < 8 and 0 <= nr < 8):
                continue
            sq = chess.square(nf, nr)
            occ = board.piece_at(sq)
            if occ is not None and occ.color == color:
                continue
            if board.is_attacked_by(enemy, sq):
                continue
            count += 1
    return count


def _attack_count(board, color, sq):
    return len(board.attackers(color, sq))


def _piece_squares(board, color, *, include_king=True):
    for sq, piece in board.piece_map().items():
        if piece.color != color:
            continue
        if not include_king and piece.piece_type == chess.KING:
            continue
        yield sq, piece


def _hanging_stats(board, color):
    enemy = OTHER[color]
    hanging = 0
    hanging_value = 0
    contested = 0
    for sq, piece in _piece_squares(board, color, include_king=False):
        enemy_attackers = _attack_count(board, enemy, sq)
        if enemy_attackers == 0:
            continue
        contested += 1
        defenders = _attack_count(board, color, sq)
        if defenders == 0:
            hanging += 1
            hanging_value += PIECE_VALUE[piece.piece_type]
    return hanging, hanging_value, contested


def _is_passed_pawn(board, color, sq):
    file0 = chess.square_file(sq)
    rank0 = chess.square_rank(sq)
    enemy = OTHER[color]
    for ep in board.pieces(chess.PAWN, enemy):
        ef = chess.square_file(ep)
        er = chess.square_rank(ep)
        if abs(ef - file0) > 1:
            continue
        if color == chess.WHITE and er > rank0:
            return False
        if color == chess.BLACK and er < rank0:
            return False
    return True


def _promotion_distance(color, sq):
    rank0 = chess.square_rank(sq)
    return 7 - rank0 if color == chess.WHITE else rank0


def king_shell_state(board, color):
    enemy = OTHER[color]
    zone = _king_zone(board, color)
    if not zone:
        return "critical"

    attacked = 0
    undefended = 0
    friendly_cover = 0
    for sq in zone:
        if board.is_attacked_by(enemy, sq):
            attacked += 1
            if not board.is_attacked_by(color, sq):
                undefended += 1
        occ = board.piece_at(sq)
        if occ is not None and occ.color == color:
            friendly_cover += 1

    safe_exits = _safe_king_exits(board, color)
    ksq = board.king(color)
    in_check = ksq is not None and board.is_attacked_by(enemy, ksq)

    if in_check and safe_exits == 0:
        return "critical"
    if attacked >= 5 or undefended >= 3:
        return "critical"
    if in_check or attacked >= 3 or (safe_exits <= 1 and attacked >= 2):
        return "fractured"
    if attacked >= 1 or undefended >= 1 or friendly_cover <= 2:
        return "pressured"
    return "safe"


def forcing_pressure_state(board, cfg):
    legal = _legal_moves_filtered(board, cfg)
    if not legal:
        return ForcingSummary("none", 0, 0, 0)

    checking = 0
    forcing = 0
    best_reply_width = 10**9

    for mv in legal:
        is_capture = board.is_capture(mv)
        board.push(mv)
        try:
            replies = _legal_moves_filtered(board, cfg)
            reply_width = len(replies)
            gave_check = board.is_check()
            if gave_check:
                checking += 1
            if gave_check or is_capture:
                forcing += 1
            if gave_check or is_capture or reply_width <= 2:
                best_reply_width = min(best_reply_width, reply_width)
        finally:
            board.pop()

    if best_reply_width == 10**9:
        best_reply_width = len(legal)

    if best_reply_width <= 1 and (checking > 0 or forcing > 0):
        return ForcingSummary("forcing+", checking, forcing, best_reply_width)
    if checking > 0 or best_reply_width <= 2:
        return ForcingSummary("forcing", checking, forcing, best_reply_width)
    if forcing > 0:
        return ForcingSummary("latent", checking, forcing, best_reply_width)
    return ForcingSummary("none", checking, forcing, best_reply_width)


def defender_dependency_state(board, color):
    enemy = OTHER[color]
    obligations = []

    for sq, piece in _piece_squares(board, color):
        if piece.piece_type == chess.KING:
            continue
        if _attack_count(board, enemy, sq) > 0:
            obligations.append(sq)

    for sq in _king_zone(board, color):
        if board.is_attacked_by(enemy, sq):
            obligations.append(sq)

    if not obligations:
        return "stable"

    load = {}
    fragile_obligations = 0
    for sq in obligations:
        defenders = list(board.attackers(color, sq))
        attackers = _attack_count(board, enemy, sq)
        if attackers >= max(1, len(defenders)):
            fragile_obligations += 1
        for d in defenders:
            load[d] = load.get(d, 0) + 1

    max_load = max(load.values(), default=0)
    if max_load >= 3 and fragile_obligations >= 2:
        return "collapsing"
    if max_load >= 2 and fragile_obligations >= 1:
        return "overloaded"
    if max_load >= 2 or fragile_obligations >= 1:
        return "shared-load"
    return "stable"


def line_fragility_state(board, color):
    enemy = OTHER[color]
    pinned = 0
    king_line_pressure = 0
    queen_line_pressure = 0

    for sq, piece in _piece_squares(board, color, include_king=False):
        if board.is_pinned(color, sq):
            pinned += 1
        if piece.piece_type == chess.QUEEN and _attack_count(board, enemy, sq) > 0:
            queen_line_pressure += 1

    ksq = board.king(color)
    if ksq is not None:
        king_line_pressure = _attack_count(board, enemy, ksq)

    if pinned >= 2 or (pinned >= 1 and king_line_pressure >= 2):
        return "explosive"
    if pinned >= 1 or king_line_pressure >= 2 or queen_line_pressure >= 1:
        return "active"
    if king_line_pressure >= 1:
        return "latent"
    return "closed"


def material_instability_state(board, color):
    hanging, hanging_value, contested = _hanging_stats(board, color)
    if hanging_value >= 5 or hanging >= 2:
        return "winning-sequence"
    if hanging >= 1 or contested >= 3:
        return "volatile"
    if contested >= 1:
        return "contestable"
    return "stable"


def race_pressure_state(board, color):
    passed = []
    for sq in board.pieces(chess.PAWN, color):
        if _is_passed_pawn(board, color, sq):
            passed.append(_promotion_distance(color, sq))
    if not passed:
        return "none"
    nearest = min(passed)
    if nearest <= 1:
        return "promotion-critical"
    if nearest <= 2:
        return "active-race"
    return "latent-race"


def initiative_state(board, color, cfg):
    if board.turn != color:
        return "neutral"
    forcing = forcing_pressure_state(board, cfg).level
    if forcing == "forcing+":
        return "forced-sequence"
    if forcing == "forcing":
        return "sustained-initiative"
    if forcing == "latent":
        return "initiative"
    return "neutral"


def extract_side_groups(board, color, cfg):
    c = _color_bool(color)
    return SideGroups(
        color=_color_str(c),
        K=king_shell_state(board, c),
        D=defender_dependency_state(board, c),
        X=line_fragility_state(board, c),
        M=material_instability_state(board, c),
        R=race_pressure_state(board, c),
        T=initiative_state(board, c, cfg),
    )


def extract_forcing_summary(board, cfg):
    return forcing_pressure_state(board, cfg)


def score_side_groups(side):
    return (
        1.5 * _rank_index(side.K, K_ORDER)
        + 1.2 * _rank_index(side.D, D_ORDER)
        + 0.9 * _rank_index(side.X, X_ORDER)
        + 1.3 * _rank_index(side.M, M_ORDER)
        + 0.7 * _rank_index(side.R, R_ORDER)
        + 0.6 * _rank_index(side.T, T_ORDER)
    )
