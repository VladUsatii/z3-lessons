# chess_rules.py
# A wrapper around python-chess and the micro-chess filters that I schemed
#
# For certificate checking, the critical invariant is:
#   At any opponent node: children.keys() == legal_moves_set(fen, cfg)
import chess
import hashlib
from dataclasses import dataclass as dc

class InvalidFEN(Exception): pass
class InvalidMove(Exception): pass

# Filtering out the moves that cause too much complexity
@dc(frozen=True)
class RulesConfig:
   allow_castling: bool = False
   allow_en_passant: bool = False
   allow_promotions: bool = True
   allow_underpromotions: bool = True
   reject_terminated_positions: bool = False

def explain_cfg(cfg: RulesConfig):
   return {
      "allow_castling": cfg.allow_castling,
      "allow_en_passant": cfg.allow_en_passant,
      "allow_promotions": cfg.allow_promotions,
      "allow_underpromotions": cfg.allow_underpromotions,
      "reject_terminated_positions": cfg.reject_terminated_positions,
   }

# Generate a board from some existing config
def board_from_fen(fen: str):
   try: return chess.Board(fen)
   except Exception as e: raise InvalidFEN(f"Invalid FEN: {fen!r} ({e})") from e

def is_underpromotion(move) -> bool: return move.promotion is not None and move.promotion != chess.QUEEN
def uci(move) -> str: return move.uci()

def filter_moves(board, moves, cfg: RulesConfig):
   out = []
   for m in moves:
      # Config filters
      if not cfg.allow_castling and board.is_castling(m): continue
      if not cfg.allow_en_passant and board.is_en_passant(m): continue
      if m.promotion is not None:
         if not cfg.allow_promotions: continue
         if not cfg.allow_underpromotions and is_underpromotion(m): continue
      out.append(m)
   return out

def side_to_move(fen: str) -> str: return "w" if board_from_fen(fen).turn == chess.WHITE else "b"
def is_check(fen: str) -> bool: return board_from_fen(fen).is_check()
def is_checkmate(fen: str) -> bool: return board_from_fen(fen).is_checkmate()
def is_stalemate(fen: str) -> bool: return board_from_fen(fen).is_stalemate()
def is_insufficient_material(fen: str) -> bool: return board_from_fen(fen).is_insufficient_material()
def normalize_fen(fen: str) -> str: return board_from_fen(fen).fen()

def legal_moves(fen: str, cfg: RulesConfig = RulesConfig()):
   b = board_from_fen(fen)
   if cfg.reject_terminated_positions and (
      b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material()
   ): return []
   return sorted(uci(m) for m in filter_moves(b, b.legal_moves, cfg))

def legal_moves_set(fen: str, cfg: RulesConfig = RulesConfig()): return set(legal_moves(fen, cfg))

# Applies UCI move to a position and returns the FEN result; gates moves by the cfg filters
def apply_move(fen: str, move_uci: str, cfg: RulesConfig = RulesConfig()):
   b = board_from_fen(fen)
   try: m = chess.Move.from_uci(move_uci)
   except Exception as e: raise InvalidMove(f"Invalid UCI move string [{move_uci!r} {e}]") from e
   if move_uci not in legal_moves_set(fen, cfg): raise InvalidMove(f"Move {move_uci!r} is not legal under [cfg={cfg} fen={fen!r}]")
   b.push(m)
   return b.fen()

# Returns final FEN after a sequence of UCI moves
def result_after_moves(fen: str, moves_uci, cfg: RulesConfig = RulesConfig()) -> str:
   cur=fen
   for move in moves_uci: cur=apply_move(cur, move, cfg)
   return cur

def is_terminal(fen: str) -> bool:
   b = board_from_fen(fen)
   return b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material()

# Keying
def state_key(fen: str):return hashlib.sha256(normalize_fen(fen).encode("utf-8")).hexdigest()
def node_id(fen, ply) -> str: return hashlib.sha256(f"{normalize_fen(fen)}\nply={ply}".encode("utf-8")).hexdigest()
