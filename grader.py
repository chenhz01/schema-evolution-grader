#!/usr/bin/env python3
"""schema-evolution-grader — grade JSON Schema evolution compatibility.

Levels (worst rule wins):
  FULL_COMPAT      old docs validate under new schema AND new docs under old
  BACKWARD_COMPAT  old docs validate under new schema (safe producer upgrade)
  FORWARD_COMPAT   new docs validate under old schema (safe consumer upgrade)
  BREAKING         neither direction is safe

Pure stdlib; read-only; fails closed (exit 2) on unreadable/invalid input.
"""
import argparse
import json
import sys

RANK = {"FULL_COMPAT": 0, "BACKWARD_COMPAT": 1, "FORWARD_COMPAT": 2, "BREAKING": 3}


def _type_of(schema):
    t = schema.get("type")
    if isinstance(t, list):
        return set(t)
    return t


def _grade_type(old, new):
    ot, nt = _type_of(old), _type_of(new)
    if ot is None and nt is None:
        return "FULL_COMPAT", []
    if ot is None:
        return "BACKWARD_COMPAT", ["new schema constrains type (was unconstrained)"]
    if nt is None:
        return "FORWARD_COMPAT", ["new schema drops type constraint"]
    oset = set(ot) if isinstance(ot, (list, set)) else {ot}
    nset = set(nt) if isinstance(nt, (list, set)) else {nt}
    if oset == nset:
        return "FULL_COMPAT", []
    if oset < nset or oset == {"integer"} and "number" in nset:
        return "FORWARD_COMPAT", ["type widened %s -> %s (old readers may reject new docs)" % (sorted(oset), sorted(nset))]
    if nset < oset:
        return "BREAKING", ["type narrowed %s -> %s (old docs may fail new schema)" % (sorted(oset), sorted(nset))]
    return "BREAKING", ["type changed %s -> %s" % (sorted(oset), sorted(nset))]


def _grade_enum(old, new):
    oe, ne = old.get("enum"), new.get("enum")
    if oe is None and ne is None:
        return "FULL_COMPAT", []
    if oe is None:
        return "BACKWARD_COMPAT", ["enum added (old docs with out-of-enum values may fail)"]
    if ne is None:
        return "FORWARD_COMPAT", ["enum removed"]
    oe, ne = set(oe), set(ne)
    if oe == ne:
        return "FULL_COMPAT", []
    if oe <= ne:
        return "BACKWARD_COMPAT", ["enum values added %s" % sorted(ne - oe)]
    if ne <= oe:
        return "BREAKING", ["enum values removed %s" % sorted(oe - ne)]
    return "BREAKING", ["enum changed: added %s, removed %s" % (sorted(ne - oe), sorted(oe - ne))]


def _grade_numeric(old, new, keys):
    notes, worst = [], "FULL_COMPAT"
    for k in keys:
        ov, nv = old.get(k), new.get(k)
        if ov == nv:
            continue
        if ov is None and nv is not None:
            worst = max_key(worst, "FORWARD_COMPAT")
            notes.append("%s added (%s) — old docs may violate" % (k, nv))
        elif nv is None:
            worst = max_key(worst, "BACKWARD_COMPAT")
            notes.append("%s removed — new docs unconstrained" % k)
        else:
            tighten = (k in ("minimum", "minLength", "minItems") and nv > ov) or (k in ("maximum", "maxLength", "maxItems") and nv < ov)
            if tighten:
                worst = max_key(worst, "BREAKING")
                notes.append("%s tightened %s -> %s" % (k, ov, nv))
            else:
                worst = max_key(worst, "FORWARD_COMPAT")
                notes.append("%s loosened %s -> %s" % (k, ov, nv))
    return worst, notes


def _grade_required(old_props, new_props, old_req, new_req):
    notes, worst = [], "FULL_COMPAT"
    added = set(new_req) - set(old_req)
    removed = set(old_req) - set(new_req)
    for r in sorted(added):
        if r not in (old_props or {}):
            continue  # brand-new required property: old docs lack it
        worst = max_key(worst, "BREAKING")
        notes.append("required added for existing property %r (old docs may lack it)" % r)
    for r in sorted(added):
        if r in (old_props or {}):
            continue
        worst = max_key(worst, "BREAKING")
        notes.append("new required property %r introduced (old docs lack it)" % r)
    for r in sorted(removed):
        if r in (new_props or {}):
            worst = max_key(worst, "FORWARD_COMPAT")
            notes.append("required dropped for %r (new docs may omit it; old schema demands it)" % r)
        else:
            worst = max_key(worst, "FORWARD_COMPAT")
            notes.append("property %r removed entirely (old docs with it still validate unless additionalProperties=false)" % r)
    return worst, notes


def _grade_properties(old, new, depth):
    old_props = old.get("properties") or {}
    new_props = new.get("properties") or {}
    notes, worst = [], "FULL_COMPAT"
    for name in sorted(set(old_props) | set(new_props)):
        o, n = old_props.get(name), new_props.get(name)
        if o is not None and n is not None:
            sub_worst, sub_notes = grade(o, n, depth + 1)
            if sub_worst != "FULL_COMPAT":
                worst = max_key(worst, sub_worst)
                notes.extend("/%s%s" % (name, x) for x in sub_notes)
        elif n is not None:
            if new.get("additionalProperties") is False:
                worst = max_key(worst, "FORWARD_COMPAT")
                notes.append("/%s property added (old readers with additionalProperties:false reject)" % name)
        else:
            worst = max_key(worst, "BACKWARD_COMPAT")
            notes.append("/%s property removed (new docs missing it fail old schema if it was required)" % name)
    return worst, notes


def max_key(a, b):
    return a if RANK[a] >= RANK[b] else b


def grade(old, new, depth=0):
    """Grade old -> new schema evolution. Returns (level, notes)."""
    if not isinstance(old, dict) or not isinstance(new, dict):
        if old is None or new is None:
            raise TypeError("schemas must be objects")
        return ("FULL_COMPAT" if old == new else "BREAKING"), ["non-object schema change"]
    if depth > 50:
        return "BREAKING", ["recursion depth exceeded"]
    worst, notes = "FULL_COMPAT", []

    w, n = _grade_type(old, new)
    worst, notes = max_key(worst, w), notes + n
    w, n = _grade_enum(old, new)
    worst, notes = max_key(worst, w), notes + n
    w, n = _grade_numeric(old, new, ["minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems"])
    worst, notes = max_key(worst, w), notes + n

    old_req, new_req = old.get("required") or [], new.get("required") or []
    w, n = _grade_required(old.get("properties"), new.get("properties"), old_req, new_req)
    worst, notes = max_key(worst, w), notes + n

    if "items" in old or "items" in new:
        oi, ni = old.get("items"), new.get("items")
        if isinstance(oi, dict) and isinstance(ni, dict):
            w, n = grade(oi, ni, depth + 1)
            worst, notes = max_key(worst, w), notes + ["/items" + x for x in n]
        elif oi is None and ni is not None:
            worst, notes = max_key(worst, "FORWARD_COMPAT"), notes + ["/items constraint added"]
        elif ni is None and oi is not None:
            worst, notes = max_key(worst, "BACKWARD_COMPAT"), notes + ["/items constraint removed"]

    w, n = _grade_properties(old, new, depth)
    worst, notes = max_key(worst, w), notes + n
    return worst, notes


def main(argv=None):
    ap = argparse.ArgumentParser(prog="schema-evolution-grader", description="Grade JSON Schema evolution compatibility (FULL/BACKWARD/FORWARD/BREAKING).")
    ap.add_argument("old", help="old schema JSON file")
    ap.add_argument("new", help="new schema JSON file")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    try:
        with open(args.old, "r", encoding="utf-8") as f:
            old = json.load(f)
        with open(args.new, "r", encoding="utf-8") as f:
            new = json.load(f)
    except (OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    if not isinstance(old, dict) or not isinstance(new, dict):
        print("error: schemas must be JSON objects", file=sys.stderr)
        return 2
    level, notes = grade(old, new)
    if args.json:
        print(json.dumps({"level": level, "notes": notes}, ensure_ascii=False, indent=2))
    else:
        print("level: %s" % level)
        for n in notes:
            print("  - %s" % n)
    return 0 if level in ("FULL_COMPAT", "BACKWARD_COMPAT", "FORWARD_COMPAT") else 1


if __name__ == "__main__":
    sys.exit(main())
