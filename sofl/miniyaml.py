"""A small YAML-subset reader so the core runs on the standard library only.

Supports: nested mappings by indentation, block lists ("- item" and "- key: value" maps), inline lists
[a, b], inline maps {a: 1, b: x}, quoted strings, ints, floats, true/false/null and # comments.
It does not support anchors, multi-line strings or tabs. If PyYAML is installed, tests cross-check
that both readers give the same result for the shipped config files.
"""
from __future__ import annotations

import re


class YamlError(ValueError):
    pass


def _strip_comment(line: str) -> str:
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _split_top(s: str) -> list[str]:
    parts, depth, q, cur = [], 0, None, []
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def scalar(s: str):
    s = s.strip()
    if s == "" or s in ("null", "~"):
        return None
    if s.startswith("[") and s.endswith("]"):
        return [scalar(p) for p in _split_top(s[1:-1])]
    if s.startswith("{") and s.endswith("}"):
        d = {}
        for p in _split_top(s[1:-1]):
            k, _, v = p.partition(":")
            d[str(scalar(k))] = scalar(v)
        return d
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d*", s):
        return float(s)
    return s


def _key_val(text: str):
    m = re.match(r"^((?:\"[^\"]*\")|(?:'[^']*')|[^:]+?):(?:\s+(.*))?$", text)
    if not m:
        return None
    return str(scalar(m.group(1))), (m.group(2) or "").strip()


def loads(text: str):
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {n}: tabs are not allowed for indentation")
        s = _strip_comment(raw)
        if s.strip():
            lines.append((len(s) - len(s.lstrip(" ")), s.strip(), n))
    pos = 0

    def block(indent):
        nonlocal pos
        if pos >= len(lines):
            return None
        if lines[pos][1].startswith("- ") or lines[pos][1] == "-":
            return seq(lines[pos][0])
        return mapping(lines[pos][0])

    def mapping(indent):
        nonlocal pos
        out = {}
        while pos < len(lines) and lines[pos][0] == indent and not lines[pos][1].startswith("- "):
            _, text, n = lines[pos]
            kv = _key_val(text)
            if kv is None:
                raise YamlError(f"line {n}: expected 'key: value'")
            k, v = kv
            pos += 1
            if v == "":
                if pos < len(lines) and (lines[pos][0] > indent or (lines[pos][0] == indent and lines[pos][1].startswith("- "))):
                    out[k] = block(lines[pos][0])
                else:
                    out[k] = None
            else:
                out[k] = scalar(v)
        if pos < len(lines) and lines[pos][0] > indent:
            raise YamlError(f"line {lines[pos][2]}: unexpected indentation")
        return out

    def seq(indent):
        nonlocal pos
        out = []
        while pos < len(lines) and lines[pos][0] == indent and (lines[pos][1].startswith("- ") or lines[pos][1] == "-"):
            _, text, n = lines[pos]
            item = text[1:].strip()
            if item == "":
                pos += 1
                out.append(block(lines[pos][0]) if pos < len(lines) and lines[pos][0] > indent else None)
                continue
            kv = _key_val(item) if not item.startswith(("[", "{", "\"", "'")) else None
            if kv is None:
                out.append(scalar(item))
                pos += 1
                continue
            # "- key: value" starts a mapping whose other keys sit at indent + 2
            child_indent = indent + 2
            lines[pos] = (child_indent, item, n)
            out.append(mapping(child_indent))
        return out

    result = block(0)
    if pos < len(lines):
        raise YamlError(f"line {lines[pos][2]}: could not parse")
    return result if result is not None else {}


def load_file(path):
    with open(path, encoding="utf-8") as fh:
        return loads(fh.read())
