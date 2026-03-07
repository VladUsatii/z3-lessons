from __future__ import annotations
import json, sys
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple, Literal
import chess_rules as R

def check_cert(cert_file: str):
   with open(cert_file, "r", encoding="utf-8") as f: obj = f.read()
   c = MateInKCert.from_json(obj)
   check_mate_in_k(c, strict_ids=True)
   print("[✓]")

class CertError(Exception): pass
class CheckError(CertError): pass
class SchemaError(CertError): pass

CertKind = Literal["mate_in_k"]
Color = Literal["w", "b"]
NodeType = Literal["prover", "opponent"]
SUPPORTED_VERSIONS: Tuple[int, ...] = (1,)

def _require(cond: bool, msg: str):
   if not cond: raise SchemaError(msg)

def _sorted_dict(d: Mapping[str, Any]) -> Dict[str, Any]:
   out = {}
   for k in sorted(d.keys()):
      v = d[k]
      out[k] = _sorted_dict(v) if isinstance(v, Mapping) else v
   return out

def _normalize_cfg_dict(cfg: Mapping[str, Any]) :
   base = R.explain_cfg(R.RulesConfig())
   unknown = set(cfg.keys()) - set(base.keys())
   _require(not unknown, f"rules has unknown keys: {sorted(unknown)}")

   out= {}
   for k, default_val in base.items():
      v = cfg.get(k, default_val)
      _require(isinstance(v, bool), f"rules[{k!r}] must be bool, got {type(v).__name__}")
      out[k] = v
   return out

def cfg_from_dict(cfg) -> R.RulesConfig:
   d = _normalize_cfg_dict(cfg)
   return R.RulesConfig(
      allow_castling=d["allow_castling"],
      allow_en_passant=d["allow_en_passant"],
      allow_promotions=d["allow_promotions"],
      allow_underpromotions=d["allow_underpromotions"],
      reject_terminated_positions=d["reject_terminated_positions"],
   )

@dataclass(frozen=True)
class CertMeta:
   tool: Optional[str] = None
   tool_version: Optional[str] = None
   created_utc: Optional[str] = None
   notes: Optional[str] = None

   def to_dict(self):
      d = {}
      if self.tool is not None: d["tool"] = self.tool
      if self.tool_version is not None: d["tool_version"] = self.tool_version
      if self.created_utc is not None: d["created_utc"] = self.created_utc
      if self.notes is not None: d["notes"] = self.notes
      return d

   @staticmethod
   def from_dict(d):
      _require(isinstance(d, Mapping), f"meta must be an object, got {type(d).__name__}")
      allowed = {"tool", "tool_version", "created_utc", "notes"}
      unknown = set(d.keys()) - allowed
      _require(not unknown, f"meta has unknown keys: {sorted(unknown)}")
      for k, v in d.items():
         _require(v is None or isinstance(v, str), f"meta[{k!r}] must be string or null")
      return CertMeta(tool=d.get("tool"), tool_version=d.get("tool_version"), created_utc=d.get("created_utc"), notes=d.get("notes"))

@dataclass(frozen=True)
class CertNode:
   fen: str
   ply: int
   move: Optional[str] = None
   child: Optional[str] = None
   children: Optional[Dict[str, str]] = None
   node_type: Optional[NodeType] = None
   comment: Optional[str] = None
   tags: Optional[List[str]] = None

   def to_dict(self) -> Dict[str, Any]:
      d = {"fen": self.fen, "ply": self.ply}
      if self.move is not None: d["move"] = self.move
      if self.child is not None: d["child"] = self.child
      if self.children is not None: d["children"] = dict(self.children)
      if self.node_type is not None: d["node_type"] = self.node_type
      if self.comment is not None: d["comment"] = self.comment
      if self.tags is not None: d["tags"] = list(self.tags)
      return d

   @staticmethod
   def from_dict(d):
      _require(isinstance(d, Mapping), f"node must be an object, got {type(d).__name__}")
      allowed = {"fen", "ply", "move", "child", "children", "node_type", "comment", "tags"}
      unknown = set(d.keys()) - allowed
      _require(not unknown, f"node has unknown keys: {sorted(unknown)}")

      fen, ply = d.get("fen"), d.get("ply")
      _require(isinstance(fen, str), "node.fen must be string")
      _require(isinstance(ply, int) and not isinstance(ply, bool), "node.ply must be int")

      move, child, children = d.get("move"), d.get("child"), d.get("children")
      if move is not None: _require(isinstance(move, str), "node.move must be string or null")
      if child is not None: _require(isinstance(child, str), "node.child must be string or null")

      if children is not None:
         _require(isinstance(children, Mapping), "node.children must be object or null")
         for k, v in children.items():
            _require(isinstance(k, str), "node.children keys must be strings (UCI)")
            _require(isinstance(v, str), "node.children values must be strings (node id)")

      node_type = d.get("node_type")
      if node_type is not None:
         _require(node_type in ("prover", "opponent"), "node.node_type must be 'prover' or 'opponent'")

      comment = d.get("comment")
      if comment is not None:
         _require(isinstance(comment, str), "node.comment must be string or null")

      tags = d.get("tags")
      if tags is not None:
         _require(isinstance(tags, list), "node.tags must be list or null")
         for t in tags: _require(isinstance(t, str), "node.tags elements must be strings")

      return CertNode(fen=fen, ply=ply, move=move, child=child, children=dict(children) if isinstance(children, Mapping) else None, node_type=node_type, comment=comment, tags=list(tags) if isinstance(tags, list) else None)

@dataclass(frozen=True)
class MateInKCert:
   version: int
   kind: CertKind
   root_fen: str
   k_plies: int
   rules: Dict[str, bool]
   prover_color: Color
   root: str
   nodes: Dict[str, CertNode]
   meta: Optional[CertMeta] = None

   def cfg(self) -> R.RulesConfig: return cfg_from_dict(self.rules)
   def expected_node_id(self, fen: str, ply: int): return R.node_id(fen, ply)
   def is_prover_turn(self, fen: str) -> bool: return R.side_to_move(fen) == self.prover_color

   def to_dict(self) -> Dict[str, Any]:
      d = {
         "version": self.version,
         "kind": self.kind,
         "root_fen": self.root_fen,
         "k_plies": self.k_plies,
         "rules": dict(self.rules),
         "prover_color": self.prover_color,
         "root": self.root,
         "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
      }
      if self.meta is not None: d["meta"] = self.meta.to_dict()
      return d

   def to_json(self, *, indent=2): return json.dumps(_sorted_dict(self.to_dict()), indent=indent, sort_keys=True)

   @staticmethod
   def from_dict(d):
      _require(isinstance(d, Mapping), f"cert must be an object, got {type(d).__name__}")
      allowed = {"version", "kind", "root_fen", "k_plies", "rules", "prover_color", "root", "nodes", "meta"}
      unknown = set(d.keys()) - allowed
      _require(not unknown, f"cert has unknown keys: {sorted(unknown)}")

      version = d.get("version")
      _require(isinstance(version, int) and not isinstance(version, bool), "cert.version must be int")
      _require(version in SUPPORTED_VERSIONS, f"unsupported cert.version={version}, supported={SUPPORTED_VERSIONS}")

      kind = d.get("kind")
      _require(kind == "mate_in_k", "cert.kind must be 'mate_in_k'")

      root_fen = d.get("root_fen")
      _require(isinstance(root_fen, str), "cert.root_fen must be string")

      k_plies = d.get("k_plies")
      _require(isinstance(k_plies, int) and not isinstance(k_plies, bool) and k_plies >= 0, "cert.k_plies must be nonnegative int")

      rules_in = d.get("rules")
      _require(isinstance(rules_in, Mapping), "cert.rules must be object")
      rules = _normalize_cfg_dict(rules_in)

      prover_color = d.get("prover_color")
      _require(prover_color in ("w", "b"), "cert.prover_color must be 'w' or 'b'")

      root = d.get("root")
      _require(isinstance(root, str), "cert.root must be string")

      nodes_in = d.get("nodes")
      _require(isinstance(nodes_in, Mapping), "cert.nodes must be object")
      nodes = {}
      for nid, node_obj in nodes_in.items():
         _require(isinstance(nid, str), "cert.nodes keys must be strings (node ids)")
         _require(isinstance(node_obj, Mapping), f"cert.nodes[{nid!r}] must be object")
         nodes[nid] = CertNode.from_dict(node_obj)

      meta = None
      if d.get("meta") is not None: meta = CertMeta.from_dict(d["meta"])

      cert = MateInKCert(version=version, kind="mate_in_k", root_fen=root_fen, k_plies=k_plies, rules=rules, prover_color=prover_color, root=root, nodes=nodes, meta=meta)
      cert.validate_structure(strict_ids=True, require_complete=True)
      return cert

   @staticmethod
   def from_json(s: str):
      try: obj = json.loads(s)
      except Exception as e: raise SchemaError(f"invalid JSON: {e}") from e
      return MateInKCert.from_dict(obj)

   def validate_structure(self, *, strict_ids: bool = True, require_complete: bool = True) -> None:
      _require(self.version in SUPPORTED_VERSIONS, f"unsupported version={self.version}")
      _require(self.kind == "mate_in_k", f"unsupported kind={self.kind!r}")
      _require(isinstance(self.k_plies, int) and not isinstance(self.k_plies, bool) and self.k_plies >= 0, "k_plies must be nonnegative int")
      _require(self.prover_color in ("w", "b"), "prover_color must be 'w' or 'b'")

      root_fen_norm = R.normalize_fen(self.root_fen)
      _require(self.root_fen == root_fen_norm, "root_fen must be normalized")

      expected_root = self.expected_node_id(self.root_fen, 0)
      if strict_ids: _require(self.root == expected_root, f"root id mismatch: cert.root={self.root} expected={expected_root}")
      _require(self.root in self.nodes, f"root node id {self.root!r} not found in nodes")

      root_node = self.nodes[self.root]
      _require(root_node.fen == self.root_fen, "root node fen must equal root_fen")
      _require(root_node.ply == 0, "root node ply must be 0")

      edges = []
      for nid, node in self.nodes.items():
         _require(isinstance(node.fen, str), f"node {nid}: fen must be string")
         _require(isinstance(node.ply, int) and not isinstance(node.ply, bool), f"node {nid}: ply must be int")
         _require(0 <= node.ply <= self.k_plies, f"node {nid}: ply out of range [0,{self.k_plies}]")

         fen_norm = R.normalize_fen(node.fen)
         _require(node.fen == fen_norm, f"node {nid}: fen must be normalized")

         if strict_ids:
            exp = self.expected_node_id(node.fen, node.ply)
            _require(nid == exp, f"node id mismatch: nid={nid} expected={exp}")

         prover_turn = self.is_prover_turn(node.fen)
         expected_type = "prover" if prover_turn else "opponent"
         if node.node_type is not None:
            _require(node.node_type == expected_type, f"node {nid}: node_type mismatch")

         # mutually exclusive shape
         _require(not (node.child is not None and node.children is not None), f"node {nid}: cannot have both child and children")
         _require(not (node.move is None and node.child is not None), f"node {nid}: child requires move")
         _require(not (node.move is not None and node.child is None), f"node {nid}: move requires child")

         if require_complete:
            if prover_turn:
               _require(node.move is not None, f"node {nid}: prover node missing move")
               _require(node.child is not None, f"node {nid}: prover node missing child")
               _require(node.children is None, f"node {nid}: prover node must not have children map")
            else:
               _require(node.children is not None, f"node {nid}: opponent node missing children map")
               _require(node.move is None, f"node {nid}: opponent node must not have move")
               _require(node.child is None, f"node {nid}: opponent node must not have child")

         if node.child is not None:
            _require(isinstance(node.child, str), f"node {nid}: child must be string")
            edges.append((nid, node.child))

         if node.children is not None:
            _require(isinstance(node.children, dict), f"node {nid}: children must be dict")
            for mv, dst in node.children.items():
               _require(isinstance(mv, str), f"node {nid}: child move key must be string")
               _require(isinstance(dst, str), f"node {nid}: child id must be string")
               edges.append((nid, dst))

      for src, dst in edges:
         _require(dst in self.nodes, f"edge {src}->{dst}: missing dst node")
         s_ply = self.nodes[src].ply
         d_ply = self.nodes[dst].ply
         _require(d_ply == s_ply + 1, f"edge {src}->{dst}: ply mismatch (src ply={s_ply}, dst ply={d_ply})")

      if require_complete:
         reachable = set()
         stack = [self.root]

         while stack:
            cur = stack.pop()
            if cur in reachable: continue
            reachable.add(cur)

            cur_node = self.nodes[cur]
            if cur_node.child is not None: stack.append(cur_node.child)
            if cur_node.children is not None: stack.extend(cur_node.children.values())

         _require(reachable == set(self.nodes.keys()), f"unreachable nodes present: {sorted(set(self.nodes.keys()) - reachable)}")

def new_empty_mate_in_k_cert(*, root_fen: str, k_plies: int, cfg=R.RulesConfig(), meta=None, strict_ids=True) -> MateInKCert:
   root_fen_n = R.normalize_fen(root_fen)
   prover_color: Color = R.side_to_move(root_fen_n)
   rules = _normalize_cfg_dict(R.explain_cfg(cfg))
   root_id = R.node_id(root_fen_n, 0)
   root_node = CertNode(fen=root_fen_n, ply=0, node_type="prover")
   cert = MateInKCert(
      version=1,
      kind="mate_in_k",
      root_fen=root_fen_n,
      k_plies=k_plies,
      rules=rules,
      prover_color=prover_color,
      root=root_id,
      nodes={root_id: root_node},
      meta=meta,
   )
   cert.validate_structure(strict_ids=strict_ids, require_complete=False)
   return cert

def check_mate_in_k(cert, strict_ids=True):
   cert.validate_structure(strict_ids=strict_ids, require_complete=True)
   cfg = cert.cfg()

   prover = cert.prover_color
   opp = "b" if prover == "w" else "w"
   stack, seen = [cert.root], set()
   while stack:
      nid = stack.pop()
      if nid in seen: continue
      seen.add(nid)

      node = cert.nodes[nid]
      fen, ply = node.fen, node.ply
      stm = R.side_to_move(fen)
      prover_turn = (stm == prover)

      if R.is_checkmate(fen):
         if stm != opp: raise CheckError(f"node {nid}: prover is checkmated (side_to_move={stm}, prover={prover})")

         legal = R.legal_moves_set(fen, cfg)
         kids = node.children if node.children is not None else {}
         if set(kids.keys()) != legal: raise CheckError(f"node {nid}: checkmate node children mismatch (expected {len(legal)}, got {len(kids)})")
         continue

      if ply == cert.k_plies: raise CheckError(f"node {nid}: reached k_plies={cert.k_plies} without checkmate")

      if prover_turn:
         mv = node.move
         child = node.child
         if mv is None or child is None: raise CheckError(f"node {nid}: prover node missing move/child")

         try: next_fen = R.apply_move(fen, mv, cfg)
         except Exception as e: raise CheckError(f"node {nid}: prover move {mv!r} failed apply_move: {e}") from e

         if child not in cert.nodes: raise CheckError(f"node {nid}: missing child node {child!r}")

         child_node = cert.nodes[child]
         if child_node.fen != next_fen: raise CheckError(f"node {nid}->{child}: fen mismatch for move {mv!r}")
         if strict_ids and child != cert.expected_node_id(next_fen, ply + 1): raise CheckError(f"node {nid}: child id mismatch for move {mv!r}")
         stack.append(child)
         continue

      kids = node.children
      if kids is None: raise CheckError(f"node {nid}: opponent node missing children")

      legal = R.legal_moves_set(fen, cfg)
      got = set(kids.keys())
      if got != legal: raise CheckError(f"node {nid}: opponent children keys mismatch (expected {len(legal)}, got {len(got)})")
      if not legal: raise CheckError(f"node {nid}: no legal moves but not checkmate (stalemate/termination)")

      for mv, dst in kids.items():
         try: next_fen = R.apply_move(fen, mv, cfg)
         except Exception as e: raise CheckError(f"node {nid}: opponent move {mv!r} failed apply_move: {e}") from e

         if dst not in cert.nodes: raise CheckError(f"node {nid}: missing dst node {dst!r} for reply {mv!r}")

         dst_node = cert.nodes[dst]
         if dst_node.fen != next_fen: raise CheckError(f"node {nid}->{dst}: fen mismatch for reply {mv!r}")
         if strict_ids and dst != cert.expected_node_id(next_fen, ply + 1): raise CheckError(f"node {nid}: dst id mismatch for reply {mv!r}")
         stack.append(dst)