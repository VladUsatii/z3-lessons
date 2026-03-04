#!/usr/bin/env python3
# Right now, this harness is actually really bad, but it'll improve as I develop the course
# to help new Z3 users prepare for frontier research
import json, os, time, traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import z3 # See installation instructions in lesson1/README.md

@dataclass(frozen=True)
class ConstraintInfo:
   cid: str    # constraint ID
   label: str  # a human label
   kind: str   # such as "grammar" or "validator"
   source: str # file:line or the function name
   sexpr: str  # expr.sexpr()

# To make solvers replayable, we assert/track UNSAT, use a log, and dump replayable artifacts
class Harness(object):
   def __init__(self, dump_dir=None, random_seed=0, timeout_ms=None, logic=None):
      self.s = z3.Solver()
      # If provided, use the logic and timeouts
      if logic is not None: self.s.set(logic=logic)
      if timeout_ms is not None: self.s.set(timeout=timeout_ms)

      # Add the random seeds
      z3.set_param("smt.random_seed", random_seed)
      z3.set_param("sat.random_seed", random_seed)

      self.random_seed = random_seed
      self.timeout_ms = timeout_ms
      self.logic = logic
      self.dump_dir = dump_dir

      self._t0 = time.time()
      self._events = []
      self._constraints = {}
      self._track_lits = {}
      self._push_depth = 0

      if dump_dir is not None:
         os.makedirs(dump_dir, exist_ok=True)
         self._write_json("meta.json", { "random_seed": random_seed, "timeout_ms": timeout_ms, "logic": logic, "t0_unix": self._t0 })
      self._log("init", {"random_seed": random_seed, "timeout_ms": timeout_ms, "logic": logic})

   def _log(self, event, data):
      rec = {"t": time.time() - self._t0, "event": event, **data}
      self._events.append(rec)
      if self.dump_dir is not None:
         with open(os.path.join(self.dump_dir, "trace.jsonl"), "a", encoding="utf-8") as f:
            f.write(f"{json.dumps(rec)}\n")

   def _write_json(self, name, obj):
      assert self.dump_dir is not None, "dump_dir must be set to _write_json"
      with open(os.path.join(self.dump_dir, name), "w", encoding="utf-8") as f:
         json.dump(obj, f, indent=2, sort_keys=True)

   def push(self):
      self.s.push()
      self._push_depth+=1
      self._log("push", {"depth": self._push_depth})

   def pop(self, n=1):
      self.s.pop(n)
      self._push_depth=max(0, self._push_depth-n)
      self._log("pop", {"n": n, "depth": self._push_depth})

   # Track each constraint with a dedicated Bool literal so we can get unsat cores
   def add_tracked(self, cid, expr, *, label, kind, source=""):
      assert cid not in self._constraints, "duplicate cid"
      t = z3.Bool(f"track__{cid}")
      self.s.assert_and_track(expr, t)

      info = ConstraintInfo(cid=cid, label=label, kind=kind, source=source, sexpr=expr.sexpr())
      self._constraints[cid] = info
      self._track_lits[cid] = t
      self._log("add", {"cid": cid, "label": label, "kind": kind, "source": source, "expr_sexpr": info.sexpr})

   # Untracked adds; use for any axioms you don't care to appear in an unsat core
   def add(self, expr, *, label="", kind="", source=""):
      self.s.add(expr)
      self._log("add_untracked", {"label": label, "kind": kind, "source": source, "expr_sexpr": expr.sexpr()})

   def snapshot_smt2(self, filename="problem.smt2"):
      assert self.dump_dir is not None, "must have a dump_dir set"
      smt2 = self.s.to_smt2()
      with open(os.path.join(self.dump_dir, filename), "w", encoding='utf-8') as f:
         f.write(smt2)
      self._log("snapshot_smt2", {"file": filename, "bytes": len(smt2)})

   def _stats_dict(self):
      st, out = self.s.statistics(), {}
      for k in st.keys(): out[str(k)] = st.get_key_value(k)
      return out

   # Executes a check-sat and dumps stats/model/core
   def check(self) -> z3.CheckSatResult:
      self._log("check_begin", {"depth": self._push_depth})
      t0 = time.time()
      try: r = self.s.check()
      except Exception as e:
         self._log("check_exception", {"err": repr(e), "traceback": traceback.format_exc()})
         raise
      self._log("check_end", {"result": str(r), "wall_s": time.time() - t0})
      self._write_json("stats.json", self._stats_dict())
      self.snapshot_smt2() # dump ss for replay at the check boundary

      if r == z3.sat:
         m = self.s.model()
         self._dump_model(m); self._audit_model(m)
      elif r == z3.unsat:
         self._dump_unsat_core()
      else:
         try: reason = self.s.reason_unknown()
         except Exception as e: reason = None
         self._write_json("unknown.json", {"reason": reason})

      self._write_json("constraints.json", {cid: asdict(info) for cid, info in self._constraints.items()})
      return r

   def _dump_model(self, m: z3.ModelRef):
      assert self.dump_dir is not None, "must have a dump_dir set"
      items = {}
      for d in m.decls(): items[d.name()] = str(m[d])
      self._write_json("model.json", items)
      self._log("model_dump", {"n_decls": len(items)})

   # Evaluate any tracked constraints and report failures
   def _audit_model(self, m: z3.ModelRef):
      fails = []

      # TODO: implement this (?)
      for cid, info in self._constraints.items(): pass

      self._write_json("audit.json", {"note": "enable expr-object storage for full audit"})
      self._log("audit", {"failures": len(fails)})

   def _dump_unsat_core(self):
      core = self.s.unsat_core() # list of tracking literals
      cids = []
      for lit in core:
         name=str(lit)
         if name.startswith("track__"): cids.append(name[7:])
         else: cids.append(name)
      infos = []
      for cid in cids:
         info = self._constraints.get(cid)
         infos.append(asdict(info) if info else {"cid": cid, "missing": True})
      self._write_json("unsat_core.json", {"core_cids": cids, "core": infos})
      self._log("unsat_core", {"size": len(cids)})

   def close(self): self._log("close", {"depth": self._push_depth})
