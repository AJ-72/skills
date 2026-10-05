#!/usr/bin/env python3
"""Validate an architecture canvas: data block parses, ids resolve, grid cells are unique,
and (with --root) every ref points at a real file and line. Exit 1 on any error."""
import argparse
import json
import re
import sys
from pathlib import Path

KINDS = {"actor", "external", "service", "module", "store", "queue"}
REF = re.compile(r"^(.+?):(\d+)(?:-(\d+))?$")


def check_ref(ref, root, where, errors):
    m = REF.match(ref)
    if not m:
        errors.append(f"{where}: ref '{ref}' is not path:line or path:start-end")
        return
    path = root / m.group(1)
    if not path.is_file():
        errors.append(f"{where}: ref file not found: {m.group(1)}")
        return
    lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    last = int(m.group(3) or m.group(2))
    if last > lines:
        errors.append(f"{where}: ref '{ref}' beyond end of file ({lines} lines)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("canvas")
    ap.add_argument("--root", help="repo root; when given, every ref and node file must exist")
    args = ap.parse_args()

    html = Path(args.canvas).read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="canvas-data">(.*?)</script>', html, re.S)
    if not m:
        sys.exit("FAIL: no #canvas-data block found")
    try:
        d = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        sys.exit(f"FAIL: #canvas-data is not valid JSON: {e}")

    errors, warns = [], []
    root = Path(args.root) if args.root else None
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    if not title or title.group(1).strip() == "Architecture Canvas":
        warns.append("<title> still the template default; set a 2-4 word name")

    nodes = d.get("nodes") or []
    ids, cells = set(), {}
    for i, n in enumerate(nodes):
        where = f"node[{i}] {n.get('id', '?')}"
        for f in ("id", "label", "kind", "col", "row", "summary"):
            if n.get(f) in (None, ""):
                errors.append(f"{where}: missing '{f}'")
        if n.get("id") in ids:
            errors.append(f"{where}: duplicate id")
        ids.add(n.get("id"))
        if n.get("kind") not in KINDS:
            errors.append(f"{where}: kind '{n.get('kind')}' not one of {sorted(KINDS)}")
        if not isinstance(n.get("col"), int) or not isinstance(n.get("row"), int) or n.get("col", 0) < 0 or n.get("row", 0) < 0:
            errors.append(f"{where}: col/row must be non-negative integers")
        else:
            cell = (n["col"], n["row"])
            if cell in cells:
                errors.append(f"{where}: grid cell {cell} already used by '{cells[cell]}'")
            cells[cell] = n.get("id")
        if len(str(n.get("label", ""))) > 24:
            warns.append(f"{where}: label longer than 24 chars will overflow the box")
        if root:
            for f in n.get("files") or []:
                if not (root / REF.sub(r"\1", f)).exists():
                    errors.append(f"{where}: file not found: {f}")

    for i, z in enumerate(d.get("zones") or []):
        if not isinstance(z.get("from"), int) or not isinstance(z.get("to"), int) or z["from"] > z["to"]:
            errors.append(f"zone[{i}] {z.get('label')}: needs integer from <= to")

    flows = d.get("flows") or []
    if not flows:
        errors.append("no flows defined")
    used, fids = set(), set()
    for fi, f in enumerate(flows):
        fwhere = f"flow[{fi}] {f.get('id', '?')}"
        if f.get("id") in fids:
            errors.append(f"{fwhere}: duplicate id")
        fids.add(f.get("id"))
        for fld in ("id", "label", "trigger"):
            if not f.get(fld):
                errors.append(f"{fwhere}: missing '{fld}'")
        steps = f.get("steps") or []
        if not steps:
            errors.append(f"{fwhere}: no steps")
        for si, s in enumerate(steps):
            where = f"{fwhere} step {si + 1}"
            for end in ("from", "to"):
                if s.get(end) not in ids:
                    errors.append(f"{where}: '{end}' = '{s.get(end)}' is not a node id")
                used.add(s.get(end))
            for fld in ("label", "detail"):
                if not s.get(fld):
                    errors.append(f"{where}: missing '{fld}'")
            if len(str(s.get("label", ""))) > 40:
                warns.append(f"{where}: label longer than 40 chars crowds the arrow; move detail to 'detail'")
            ref = s.get("ref")
            if not ref and not s.get("inferred"):
                errors.append(f"{where}: no 'ref' — give file:line or mark inferred")
            if ref and root:
                check_ref(ref, root, where, errors)

    for n in nodes:
        if n.get("id") not in used:
            warns.append(f"node {n.get('id')}: not used by any flow")
    if "</" in m.group(1):
        errors.append("data block contains '</' which can close the script tag; write '<\\/' instead")

    for w in warns:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        sys.exit(f"FAIL: {len(errors)} error(s)")
    steps = sum(len(f.get("steps") or []) for f in flows)
    print(f"OK: {len(nodes)} nodes, {len(flows)} flows, {steps} steps" + ("" if root else " (refs not checked: no --root)"))


if __name__ == "__main__":
    main()
