#!/usr/bin/env python3
"""self_test.py for schema-evolution-grader — [A] functional / [B] exception paths / [C] extreme edges."""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grader  # noqa: E402

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, True))
    except Exception as e:  # noqa: BLE001
        RESULTS.append((name, False))
        print("  [FAIL] %s -> %r" % (name, e))


def assert_eq(a, b, msg=""):
    assert a == b, msg or "%r != %r" % (a, b)


def assert_true(c, m=""):
    assert c, m


def lvl(old, new):
    return grader.grade(old, new)[0]


def notes(old, new):
    return grader.grade(old, new)[1]


# ---------- [A] functional ----------
def a01(): assert_eq(lvl({}, {}), "FULL_COMPAT")
def a02(): assert_eq(lvl({"type": "string"}, {"type": "string"}), "FULL_COMPAT")
def a03(): assert_eq(lvl({"type": "string"}, {"type": "integer"}), "BREAKING")
def a04(): assert_eq(lvl({"type": "string"}, {"type": ["string", "null"]}), "FORWARD_COMPAT")
def a05(): assert_eq(lvl({"type": ["string", "null"]}, {"type": "string"}), "BREAKING")
def a06(): assert_eq(lvl({"enum": [1, 2]}, {"enum": [1, 2, 3]}), "BACKWARD_COMPAT")
def a07(): assert_eq(lvl({"enum": [1, 2, 3]}, {"enum": [1, 2]}), "BREAKING")
def a08(): assert_eq(lvl({"type": "string", "minLength": 1}, {"type": "string", "minLength": 5}), "BREAKING")
def a09(): assert_eq(lvl({"type": "string", "minLength": 5}, {"type": "string", "minLength": 1}), "FORWARD_COMPAT")
def a10(): assert_eq(lvl({"type": "integer", "maximum": 100}, {"type": "integer", "maximum": 200}), "FORWARD_COMPAT")
def a11(): assert_eq(lvl({"type": "object", "properties": {"a": {}}}, {"type": "object", "properties": {"a": {}, "b": {}}}), "FULL_COMPAT")
def a12(): assert_eq(lvl({"type": "object", "required": ["a"]}, {"type": "object", "required": ["a", "b"]}), "BREAKING")
def a13(): assert_eq(lvl({"type": "object", "properties": {"a": {"type": "string"}}}, {"type": "object"}), "BACKWARD_COMPAT")
def a14():
    n = notes({"type": "integer", "maximum": 10}, {"type": "integer", "maximum": 20})
    assert_true(any("loosened" in x for x in n))
def a15(): assert_eq(lvl({"minimum": 0}, {"minimum": 0}), "FULL_COMPAT")
def a16(): assert_eq(lvl({}, {"minimum": 5}), "FORWARD_COMPAT")
def a17(): assert_eq(lvl({"minimum": 5}, {}), "BACKWARD_COMPAT")
def a18(): assert_eq(lvl({"items": {"type": "string"}}, {"items": {"type": "string"}}), "FULL_COMPAT")
def a19(): assert_eq(lvl({"items": {"type": "string"}}, {"items": {"type": "integer"}}), "BREAKING")
def a20(): assert_eq(lvl({"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}, {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}), "FULL_COMPAT")
def a21():
    n = notes({"type": "object", "properties": {"a": {"type": "string"}}}, {"type": "object", "properties": {"a": {"type": "integer"}}})
    assert_true(any(x.startswith("/a") for x in n), "nested notes carry property path")
def a22(): assert_eq(lvl({"type": "object"}, {"type": "object", "properties": {"x": {"enum": [1]}}}), "FULL_COMPAT", "new unconstrained-before property")
def a23():
    old = {"type": "object", "properties": {"cfg": {"type": "object", "properties": {"deep": {"type": "string"}}}}}
    new = {"type": "object", "properties": {"cfg": {"type": "object", "properties": {"deep": {"type": "integer"}}}}}
    assert_eq(lvl(old, new), "BREAKING")
def a24(): assert_eq(lvl({"enum": [1]}, {"enum": [1]}), "FULL_COMPAT")
def a25():
    r = grader.grade({"type": "string"}, {"type": "string"})
    assert_true(isinstance(r, tuple) and isinstance(r[1], list))
def a26():
    old = {"type": "object", "properties": {"a": {}}, "additionalProperties": False}
    new = {"type": "object", "properties": {"a": {}, "b": {}}, "additionalProperties": False}
    assert_eq(lvl(old, new), "FORWARD_COMPAT")
def a27(): assert_eq(lvl({"maxLength": 10}, {"maxLength": 20}), "FORWARD_COMPAT")
def a28(): assert_eq(lvl({"minItems": 2}, {"minItems": 1}), "FORWARD_COMPAT")
def a29(): assert_eq(lvl({"type": ["string", "integer"]}, {"type": ["integer", "string"]}), "FULL_COMPAT")
def a30():
    here = os.path.dirname(os.path.abspath(__file__))
    fd1, p1 = tempfile.mkstemp(suffix=".json")
    fd2, p2 = tempfile.mkstemp(suffix=".json")
    os.close(fd1)
    os.close(fd2)
    try:
        open(p1, "w").write('{"type": "string"}')
        open(p2, "w").write('{"type": "integer"}')
        code = subprocess.run([sys.executable, os.path.join(here, "grader.py"), p1, p2], capture_output=True, text=True)
        assert_eq(code.returncode, 1)
        assert_true("BREAKING" in code.stdout)
    finally:
        os.unlink(p1)
        os.unlink(p2)

# ---------- [B] exception paths ----------
def b01():
    code = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "grader.py"), "missing1.json", "missing2.json"], capture_output=True, text=True)
    assert_eq(code.returncode, 2)
def b02():
    here = os.path.dirname(os.path.abspath(__file__))
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        open(p, "w").write("{invalid")
        code = subprocess.run([sys.executable, os.path.join(here, "grader.py"), p, p], capture_output=True, text=True)
        assert_eq(code.returncode, 2)
    finally:
        os.unlink(p)
def b03():
    code = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "grader.py")], capture_output=True, text=True)
    assert_eq(code.returncode, 2)
def b04():
    here = os.path.dirname(os.path.abspath(__file__))
    code = subprocess.run([sys.executable, os.path.join(here, "grader.py"), "--help"], capture_output=True, text=True)
    assert_eq(code.returncode, 0)
def b05():
    here = os.path.dirname(os.path.abspath(__file__))
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        open(p, "w").write('[1, 2]')
        code = subprocess.run([sys.executable, os.path.join(here, "grader.py"), p, p], capture_output=True, text=True)
        assert_eq(code.returncode, 2, "non-object schema rejected")
    finally:
        os.unlink(p)
def b06():
    try:
        grader.grade(None, {})
        assert False
    except TypeError:
        pass
def b07(): assert_eq(lvl([], []), "FULL_COMPAT", "degenerate list schemas tolerated in-process")
def b08():
    here = os.path.dirname(os.path.abspath(__file__))
    fd1, p1 = tempfile.mkstemp(suffix=".json")
    fd2, p2 = tempfile.mkstemp(suffix=".json")
    os.close(fd1)
    os.close(fd2)
    try:
        open(p1, "w").write('{"type": "string"}')
        open(p2, "w").write('{"type": "string"}')
        code = subprocess.run([sys.executable, os.path.join(here, "grader.py"), p1, p2, "--json"], capture_output=True, text=True)
        rep = json.loads(code.stdout)
        assert_eq(rep["level"], "FULL_COMPAT")
        assert_eq(rep["notes"], [])
    finally:
        os.unlink(p1)
        os.unlink(p2)
def b09():
    code = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "grader.py"), "onlyone.json"], capture_output=True, text=True)
    assert_eq(code.returncode, 2)
def b10(): assert_true(grader.RANK["FULL_COMPAT"] < grader.RANK["BREAKING"])

# ---------- [C] extreme edges ----------
def c01():
    deep_old = {"type": "object", "properties": {"a": deep_old}} if False else None
    old = {"type": "string"}
    new = {"type": "string", "enum": ["a"]}
    assert_eq(lvl(old, new), "BACKWARD_COMPAT")
def c02():
    old = {"enum": ["a", "b"]}
    new = {"enum": ["b", "c"]}
    assert_eq(lvl(old, new), "BREAKING")
def c03():
    old = {"type": "object", "required": ["x"]}
    new = {"type": "object"}
    assert_eq(lvl(old, new), "FORWARD_COMPAT")
def c04():
    old = {"type": "object", "properties": {"a": {}}, "required": ["a"]}
    new = {"type": "object", "properties": {"a": {}}}
    assert_eq(lvl(old, new), "FORWARD_COMPAT")
def c05():
    old = {"type": "object", "properties": {"a": {}}}
    new = {"type": "object", "properties": {"a": {}}, "required": ["a"]}
    assert_eq(lvl(old, new), "BREAKING")
def c06():
    old = {"minimum": 0, "maximum": 100}
    new = {"minimum": 0, "maximum": 100}
    assert_eq(lvl(old, new), "FULL_COMPAT")
def c07():
    n = notes({"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": False},
              {"type": "object", "properties": {"a": {}, "b": {}}, "additionalProperties": False})
    assert_true(any("/b" in x for x in n))
def c08():
    deep = {"type": "object"}
    cur = deep
    for i in range(60):
        cur["properties"] = {"n%d" % i: {"type": "object"}}
        cur = cur["properties"]["n%d" % i]
    old = json.loads(json.dumps(deep))
    new = json.loads(json.dumps(deep))
    new["properties"]["n0"]["properties"]["n1"]["type"] = "string"
    r = grader.grade(old, new)
    assert_true(r[0] in ("FULL_COMPAT", "BREAKING"))
def c09():
    uni_old = {"type": "string", "enum": ["\u4e2d\u6587"]}
    uni_new = {"type": "string", "enum": ["\u4e2d\u6587", "\u65e5\u672c\u8a9e"]}
    assert_eq(lvl(uni_old, uni_new), "BACKWARD_COMPAT")
def c10():
    old = {"maximum": 1e308}
    new = {"maximum": 1e308}
    assert_eq(lvl(old, new), "FULL_COMPAT")
def c11():
    old = {"maxLength": 0}
    new = {"maxLength": 0}
    assert_eq(lvl(old, new), "FULL_COMPAT")
def c12():
    old = {"type": "integer"}
    new = {"type": "number"}
    assert_eq(lvl(old, new), "FORWARD_COMPAT")
def c13():
    old = {"items": {"enum": [1]}}
    new = {"items": {"enum": [1, 2]}}
    assert_eq(lvl(old, new), "BACKWARD_COMPAT")
def c14():
    r1 = grader.grade({"type": "string"}, {"type": "integer"})
    r2 = grader.grade({"type": "string"}, {"type": "integer"})
    assert_eq(r1, r2)
def c15():
    n = notes({"enum": [1, 2, 3]}, {"enum": [3, 4]})
    assert_true(any("added" in x for x in n) and any("removed" in x for x in n))
def c16():
    old = {"type": "object", "properties": {"a": {"minimum": 5}}}
    new = {"type": "object", "properties": {"a": {"minimum": 1}}}
    n = notes(old, new)
    assert_true(any("/a" in x and "loosened" in x for x in n))

for fn in sorted([v for k, v in list(globals().items()) if k.startswith(("a0", "a1", "a2", "a3", "b0", "b1", "c0", "c1"))], key=lambda f: f.__name__):
    check(fn.__name__, fn)


# ---------- [R2] round-2 additions (numeric widening semantics, direction matrix, path notes) ----------
def r201(): assert_eq(lvl({"type": "number"}, {"type": "integer"}), "BREAKING", "number->integer narrows")
def r202(): assert_eq(lvl({"type": "integer"}, {"type": "number"}), "FORWARD_COMPAT", "integer->number widens")
def r203(): assert_eq(lvl({"type": ["integer", "null"]}, {"type": "number"}), "BREAKING", "null docs fail under number")
def r204(): assert_eq(lvl({"type": "number"}, {"type": ["number", "string"]}), "FORWARD_COMPAT")
def r205():
    old = {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}
    new = {"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}
    assert_eq(lvl(old, new), "FORWARD_COMPAT")
def r206():
    n = notes({"type": "object", "properties": {"a": {"items": {"type": "integer"}}}},
              {"type": "object", "properties": {"a": {"items": {"type": "number"}}}})
    assert_true(any("/a/items" in x for x in n), "nested items path preserved")
def r207(): assert_eq(lvl({"type": "string", "minLength": 3}, {"type": "string", "minLength": 3, "maxLength": 5}), "FORWARD_COMPAT")
def r208(): assert_eq(lvl({"type": "string", "maxLength": 5}, {"type": "string", "maxLength": 50}), "FORWARD_COMPAT")
def r209(): assert_eq(lvl({"type": "string", "minLength": 5}, {"type": "string", "minLength": 50}), "BREAKING")
def r210():
    old = {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "string"}}}
    new = {"type": "object", "properties": {"a": {"type": "string"}}}
    n = notes(old, new)
    assert_true(any("/b" in x for x in n))
def r211():
    try:
        grader.grade(None, {})
        assert False
    except TypeError:
        pass
def r212(): assert_eq(lvl({"type": "string"}, {"type": "string"}), "FULL_COMPAT")  # stability sentinel
def r213():
    old = {"enum": [1]}
    new = {"enum": [1], "type": "integer"}
    assert_eq(lvl(old, new), "BACKWARD_COMPAT")

for fn in sorted([v for k, v in list(globals().items()) if k.startswith("r2")], key=lambda f: f.__name__):
    check(fn.__name__, fn)

passed = sum(1 for _, ok_ in RESULTS if ok_)
for n, ok_ in RESULTS:
    if not ok_:
        print("FAIL:", n)
print("SUMMARY: PASS %d/%d" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
