#!/usr/bin/env python3
"""Writes tests/python-samples.valk: YAML read by PyYAML, as the expected answers for
tests/crosscheck.valk.

PyYAML reads YAML 1.1, so it is given the YAML 1.2 core schema's rules for plain scalars here;
the documents are built from its nodes the way this package builds them (keys as written, merge
keys first). ruamel.yaml, which reads YAML 1.2 itself, must agree on every sample. Run it again
after changing it:

    pip install pyyaml ruamel.yaml
    python3 tests/crosscheck.py
"""

import json
import math
import os
import random
import re

import yaml
from ruamel.yaml import YAML

HERE = os.path.dirname(os.path.abspath(__file__))


class CoreLoader(yaml.SafeLoader):
    """PyYAML's parser with YAML 1.2 core schema resolution"""


CoreLoader.yaml_implicit_resolvers = {}
for tag, regexp, first in [
    ("tag:yaml.org,2002:null", r"^(?:~|null|Null|NULL|)$", list("~nN") + [""]),
    ("tag:yaml.org,2002:bool", r"^(?:true|True|TRUE|false|False|FALSE)$", list("tTfF")),
    ("tag:yaml.org,2002:int", r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$", list("-+0123456789")),
    ("tag:yaml.org,2002:float", r"^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
     r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$", list("-+0123456789.")),
    ("tag:yaml.org,2002:merge", r"^(?:<<)$", ["<"]),
]:
    CoreLoader.add_implicit_resolver(tag, re.compile(regexp), first)


class Unsupported(Exception):
    pass


class Duplicate(Exception):
    pass


def core_int(text):
    if text.startswith("0o"):
        return int(text[2:], 8)
    if text.startswith("0x"):
        return int(text[2:], 16)
    return int(text)


def core_float(text):
    lower = text.lower()
    if lower in (".inf", "+.inf"):
        return math.inf
    if lower == "-.inf":
        return -math.inf
    if lower == ".nan":
        return math.nan
    return float(text)


def scalar(node):
    tag, text = node.tag, node.value
    if tag.endswith(":null"):
        return None
    if tag.endswith(":bool"):
        if text not in ("true", "True", "TRUE", "false", "False", "FALSE"):
            raise ValueError("not a bool")
        return text.lower() == "true"
    if tag.endswith(":int"):
        return core_int(text)
    if tag.endswith(":float"):
        return core_float(text)
    return text


def build(node, depth=0):
    if depth > 200:
        raise Unsupported("deep")
    kind = type(node).__name__
    if kind == "ScalarNode":
        return scalar(node)
    if kind == "SequenceNode":
        return [build(item, depth + 1) for item in node.value]
    merged = {}
    own = {}
    for key_node, value_node in node.value:
        if type(key_node).__name__ != "ScalarNode":
            raise Unsupported("complex key")
        if key_node.tag.endswith(":merge"):
            value = build(value_node, depth + 1)
            for source in value if isinstance(value, list) else [value]:
                if not isinstance(source, dict):
                    raise ValueError("merge needs a mapping")
                for k, v in source.items():
                    merged.setdefault(k, v)
            continue
        key = key_node.value
        if key in own:
            raise Duplicate(key)
        own[key] = build(value_node, depth + 1)
    merged.update(own)
    return merged


def py_read(text):
    """The documents, or None when PyYAML refuses the text"""
    try:
        return [build(node) for node in yaml.compose_all(text, Loader=CoreLoader)]
    except (yaml.YAMLError, Duplicate, ValueError):
        return None


def ruamel_read(text):
    loader = YAML(typ="safe", pure=True)
    try:
        return [build(node) for node in loader.compose_all(text)]
    except Unsupported:
        raise
    except Exception:
        return None


def canonical(documents):
    """JSON with markers for what JSON cannot hold, as tests/crosscheck.valk writes it"""

    def fix(value):
        if isinstance(value, float):
            if math.isnan(value):
                return "<nan>"
            if math.isinf(value):
                return "<inf>" if value > 0 else "<-inf>"
            return value
        if isinstance(value, list):
            return [fix(v) for v in value]
        if isinstance(value, dict):
            return {k: fix(v) for k, v in value.items()}
        return value

    return json.dumps(fix(documents), ensure_ascii=False)


def same(a, b):
    return canonical(a) == canonical(b)


def valk_string(text):
    out = []
    for ch in text:
        code = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "%":
            out.append("\\%")
        elif code < 0x20 or code == 0x7F:
            out.append("\\x%02x" % code)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


# Documents picked by hand: every feature, and the ways real files go wrong
HANDMADE = [
    "",
    "# only a comment\n",
    "a: 1\n",
    "a: 1\nb: two\nc: 3.5\n",
    "key: value # comment\n# a comment line\nother: x\n",
    "- a\n- b\n- c\n",
    "- 1\n- -2\n- +3\n- 0o17\n- 0x1f\n- 0x1F\n- 017\n",
    "- 1.5\n- -1.5e3\n- .5\n- 1.\n- 1e3\n- 6.02E+23\n- .inf\n- -.Inf\n- +.INF\n- .nan\n- .NaN\n",
    "- null\n- Null\n- NULL\n- ~\n-\n- nil\n- None\n",
    "- true\n- True\n- TRUE\n- false\n- yes\n- no\n- on\n- off\n- y\n- n\n",
    "- '1'\n- \"true\"\n- 'null'\n- \"~\"\n",
    "- 12:30\n- 2001-12-14\n- 2001-12-14t21:59:43.10-05:00\n- 1.2.3\n- 127.0.0.1\n",
    "- 9223372036854775807\n- -9223372036854775808\n",
    "a:\n  b:\n    c: deep\n  d: 2\ne: 3\n",
    "list:\n- a\n- b\nnext: 1\n",
    "list:\n  - a\n  - b\nnext: 1\n",
    "- a: 1\n  b: 2\n- c: 3\n",
    "- - a\n  - b\n- - c\n",
    "- - - x\n",
    "- a: - 1\n",
    "-\n  a: 1\n-\n  - x\n",
    "a:\n  - b: 1\n    c:\n      - d\n",
    "a: [1, 2, 3]\nb: {c: 1, d: [x, y]}\n",
    "[a, b, c]\n",
    "{a: 1, b: 2}\n",
    "[]\n",
    "{}\n",
    "a: []\nb: {}\nc: [[], {}]\n",
    "[a, [b, [c, [d]]]]\n",
    "{a: {b: {c: {}}}}\n",
    "[a, b, ]\n",
    "{a: 1, b: 2, }\n",
    "[\n  a,\n  b\n]\n",
    "{\n  a: 1,\n  # comment\n  b: 2\n}\n",
    "key: [\n  a,\n  b,\n]\n",
    "[a: 1, b: 2]\n",
    "{a, b: 2}\n",
    "{\"a\":1,\"b\":[true,false,null]}\n",
    "[\"a\":1]\n",
    "{a: [1, {b: 2}], c: \"x, y\"}\n",
    "[a b, c d]\n",
    "[a\n  b, c]\n",
    "{url: http://example.com:80/path}\n",
    "[a:b, c]\n",
    "- 'single'\n- 'it''s'\n- ''\n- '#not a comment'\n",
    "- \"double\"\n- \"tab\\there\"\n- \"nl\\nhere\"\n- \"quote \\\" and slash \\\\\"\n",
    "- \"\\0\\a\\b\\t\\n\\v\\f\\r\\e\\ \\\"\\/\\\\\\N\\_\\L\\P\"\n",
    "- \"\\x41\\u00e9\\U0001F600\"\n",
    "- \"multi\n  line\n\n  text\"\n",
    "- 'multi\n  line\n\n\n  text'\n",
    "- \"escaped \\\n  break\"\n",
    "- \"trailing   \n  spaces\"\n",
    "- \"escaped space\\ \n  kept\"\n",
    "a: plain\n  over\n  lines\n",
    "a: plain\n\n  with empty\n\n\n  lines\n",
    "- plain\n  in a sequence\n",
    "plain text\nat the top\n",
    "a: x # comment\n  # not a continuation\n",
    "a: value: with colon\n",
    "a: b:c\n",
    "a: 'b': c\n",
    "url: http://example.com\n",
    "a: x#y\n",
    "a: -x\nb: ?x\nc: :x\n",
    "a: |\n  literal\n  text\n",
    "a: |\n  keep\n\n\n",
    "a: |-\n  strip\n\n\n",
    "a: |+\n  keep all\n\n\n",
    "a: |+\n  keep all\n\nb: 1\n",
    "a: |\n  one\n    more indented\n  back\n",
    "a: |2\n    two extra\n  base\n",
    "a: |1-\n  leading space\n",
    "- |\n  in seq\n- >\n  folded\n",
    "a: >\n  folded\n  text\n\n  next para\n",
    "a: >\n  folded\n    more indented\n  back\n\n\n",
    "a: >-\n\n  leading empty\n",
    "a: >\n trailing\n\n",
    "a: |\n\n  after empty\n",
    "a: |\nb: 1\n",
    "a: >+\n\n",
    "a: | # comment\n  text\n",
    "--- |\n  top level\n",
    "--- >\n folded\n top\n",
    "base: &base\n  a: 1\n  b: 2\nderived:\n  <<: *base\n  b: 3\n",
    "a: &x 1\nb: *x\nc: [*x, *x]\n",
    "a: &s [1, 2]\nb: *s\n",
    "one: &one {a: 1, b: 1}\ntwo: &two {b: 2, c: 2}\nboth:\n  <<: [*one, *two]\n  d: 4\n",
    "x: &x {a: 1}\ny: {<<: *x, b: 2}\n",
    "&anchor top: value\nother: *anchor\n",
    "a: &a\n  b: 1\nc: *a\n",
    "a: &a\n- 1\n- 2\nb: *a\n",
    "\"<<\": not a merge\n",
    "---\na: 1\n---\nb: 2\n",
    "--- 1\n--- 2\n...\n",
    "---\n---\n",
    "a: 1\n...\n",
    "%YAML 1.2\n---\na: 1\n",
    "%TAG !e! tag:example.com,2000:\n---\na: !e!thing 1\n",
    "- !!str 123\n- !!int \"42\"\n- !!float 1\n- !!bool \"true\"\n- !!null \"\"\n- !!str\n",
    "- !!str true\n- !local value\n- !<tag:yaml.org,2002:str> 5\n",
    "a: !!map {b: 1}\nc: !!seq [1]\n",
    "\"quoted key\": 1\n'single key': 2\n",
    "1: one\n2.5: two\ntrue: three\nnull: four\n~: five\n",
    "a b c: spaced key\n",
    "key with: colon\n",
    "\"a\": 1\n\"b\" : 2\n",
    "é: ü\n日本: 語\n",
    "emoji: 😀\n",
    "\ufeffa: bom\n",
    "a: 1\r\nb: 2\r\n",
    "a:    \n  b: 1\n",
    "  a: 1\n  b: 2\n",
    "- a\n  # comment\n- b\n",
    "a:\n\n\n  b: 1\n",
    "[a, b]: c\n",
    "a: [1, 2\n",
    "a: {b: 1\n",
    "a: \"unclosed\n",
    "a: 'unclosed\n",
    "a: b: c\n",
    "a:\n  b: 1\n c: 2\n",
    "a: 1\na: 2\n",
    "{a: 1, a: 2}\n",
    "- a\nb: 1\n",
    "a: 1\n- b\n",
    "a: *unknown\n",
    "a: \"\\q\"\n",
    "a: @x\n",
    "a: `x\n",
    "- [a, b]]\n",
    "a: |\n   \n  x\n",
    "a:\n\t- x\n",
    "key: value\n  indented: more\n",
    "%YAML 1.2\n%YAML 1.2\n---\na\n",
    "a: &a &b 1\n",
    "a: !!int x\n",
    "a: !!float x\n",
    "a: !!bool x\n",
    "<<: 1\n",
]


WORDS = ["a", "b", "key", "value", "x y", "true", "1", "1.5", "null", "~", "- dash", "? q", ": c",
         "#hash", "a #b", "a: b", "'q'", '"dq"', "é", "日本", "😀", "line\nbreak", "tab\there",
         "  lead", "trail  ", "", "---", "...", "[x]", "{y}", "a,b", "*star", "&amp", "!bang",
         "|pipe", ">gt", "%pct", "@at", "`tick", "\\back", "yes", "no", "on", "0x1f", "0o17",
         "1e5", ".inf", "-.inf", ".nan", "12:30", "2001-12-14", "\x07bell", "\x1bescape",
         "\u2028", "\u0085", "a\n\nb\n", "x\n", "\n", "end\n\n", "0755", "1_000", "0b101", "+12",
         "1:30:00", "1.", "Yes", "OFF", "nan", "inf", "127.0.0.1", "v1.2.3", " ", "a:", "- ", "?", "<<",
         "  indented\nlines\n", "\ttab first\nline\n"]


def random_value(rng, depth):
    roll = rng.random()
    if depth > 3 or roll < 0.45:
        pick = rng.random()
        if pick < 0.5:
            return rng.choice(WORDS)
        if pick < 0.65:
            return rng.randint(-10 ** 6, 10 ** 6)
        if pick < 0.8:
            return rng.choice([0.5, -1.25, 1e20, 3.14159, 1e-7, 2.0, 0.0])
        if pick < 0.9:
            return rng.choice([True, False])
        return None
    if roll < 0.7:
        return [random_value(rng, depth + 1) for _ in range(rng.randint(0, 4))]
    return {rng.choice(WORDS[:40]): random_value(rng, depth + 1) for _ in range(rng.randint(0, 4))}


def random_documents(rng, count):
    """Random trees as PyYAML writes them, in the styles it can write"""
    styles = [
        dict(default_flow_style=False),
        dict(default_flow_style=True),
        dict(default_flow_style=None),
        dict(default_flow_style=False, indent=4),
        dict(default_flow_style=False, width=20),
        dict(default_flow_style=False, allow_unicode=True),
        dict(default_flow_style=False, explicit_start=True, explicit_end=True),
        dict(default_flow_style=False, default_style='"'),
        dict(default_flow_style=False, default_style="'"),
        dict(default_flow_style=False, default_style="|"),
        dict(default_flow_style=False, default_style=">"),
    ]
    texts = []
    while len(texts) < count:
        value = random_value(rng, 0)
        style = rng.choice(styles)
        try:
            text = yaml.dump(value, Dumper=yaml.SafeDumper, sort_keys=False, **style)
        except yaml.YAMLError:
            continue
        texts.append(text)
    return texts


def main():
    rng = random.Random(1202)
    samples = []
    for text in HANDMADE + random_documents(rng, 600):
        # Python reads NEL, LS and PS as line breaks, as YAML 1.1 did; YAML 1.2 does not
        if any(ch in text for ch in "\x85\u2028\u2029"):
            continue
        try:
            ours = py_read(text)
            theirs = ruamel_read(text)
        except Unsupported:
            continue
        if ours is None and theirs is None:
            samples.append((text, None))
            continue
        if ours is None or theirs is None or not same(ours, theirs):
            # The readers disagree: not a sample either answer can be trusted for
            if os.environ.get("SHOW_DISAGREEMENTS"):
                print("disagree:", repr(text)[:120], "|", ours and canonical(ours)[:150], "|", theirs and canonical(theirs)[:150])
            continue
        samples.append((text, canonical(ours)))

    out = []
    out.append("// Generated by tests/crosscheck.py from PyYAML and ruamel.yaml; do not edit.")
    out.append("")
    out.append("// YAML text, and its documents as JSON; `json` is empty where both readers refuse the text")
    out.append("class Sample {")
    out.append("    text: String")
    out.append("    json: String")
    out.append("}")
    out.append("")
    out.append("fn python_samples() Array[Sample] {")
    out.append("    return .{")
    for text, expected in samples:
        out.append("        Sample { text: %s, json: %s }" % (valk_string(text), valk_string(expected or "")))
    out.append("    }")
    out.append("}")
    with open(os.path.join(HERE, "python-samples.valk"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("%d samples, %d refused" % (len(samples), sum(1 for _, e in samples if e is None)))


if __name__ == "__main__":
    main()
