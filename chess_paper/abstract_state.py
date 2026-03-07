
from __future__ import annotations

import json
from dataclasses import dataclass

import chess_rules as R
from abstract_groups import ForcingSummary, SideGroups, extract_forcing_summary, extract_side_groups


@dataclass(frozen=True)
class AbstractState:
    fen: str
    stm: str
    focus_color: str
    focus: SideGroups
    opponent: SideGroups
    forcing: ForcingSummary

    @staticmethod
    def from_fen(fen, cfg=R.RulesConfig(), focus_color=None):
        fen = R.normalize_fen(fen)
        stm = R.side_to_move(fen)
        focus = stm if focus_color is None else focus_color
        opp = "b" if focus == "w" else "w"
        board = R.board_from_fen(fen)
        return AbstractState(
            fen=fen,
            stm=stm,
            focus_color=focus,
            focus=extract_side_groups(board, focus, cfg),
            opponent=extract_side_groups(board, opp, cfg),
            forcing=extract_forcing_summary(board, cfg),
        )

    def to_dict(self):
        return {
            "fen": self.fen,
            "stm": self.stm,
            "focus_color": self.focus_color,
            "focus": self.focus.to_dict(),
            "opponent": self.opponent.to_dict(),
            "forcing": self.forcing.to_dict(),
        }

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
