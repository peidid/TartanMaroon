"""Parse catalog prerequisite text into a :class:`PrereqExpr` AST.

Grammar (recursive descent, ``or`` binds loosest):

    or_expr  := and_expr ( "or"  and_expr )*
    and_expr := factor   ( "and" factor   )*
    factor   := "(" or_expr ")" | atom
    atom     := COURSE [ "at least" GRADE ]
    COURSE   := [A-Za-z0-9]{2} "-" [0-9]{3}      # 15-122, 09-222, QC-211
    GRADE    := [A-D][+-]?

``[]`` brackets in the source are always empty and are skipped.
:func:`parse_prereqs` returns ``None`` for empty or unparseable text so callers
can fall back gracefully (and ETL can count the residue).
"""

from __future__ import annotations

import re
from typing import Optional

from .ast import And, Atom, Or, PrereqExpr

_LEX = re.compile(
    r"""
      (?P<WS>\s+)
    | (?P<LP>\()
    | (?P<RP>\))
    | (?P<BR>\[[^\]]*\])
    | (?P<GRADE>at\s+least\s+(?P<G>[A-Da-d][+-]?))
    | (?P<AND>\band\b)
    | (?P<OR>\bor\b)
    | (?P<COURSE>[A-Za-z0-9]{2}-\d{3})
    """,
    re.IGNORECASE | re.VERBOSE,
)


class PrereqParseError(Exception):
    """Raised internally when text does not match the grammar."""


def _tokenize(text: str) -> list[tuple[str, Optional[str]]]:
    toks: list[tuple[str, Optional[str]]] = []
    pos, n = 0, len(text)
    while pos < n:
        m = _LEX.match(text, pos)
        if not m:
            raise PrereqParseError(f"unexpected input near {text[pos:pos + 20]!r}")
        pos = m.end()
        if m.group("WS") is not None or m.group("BR") is not None:
            continue
        if m.group("LP") is not None:
            toks.append(("LP", None))
        elif m.group("RP") is not None:
            toks.append(("RP", None))
        elif m.group("GRADE") is not None:
            toks.append(("GRADE", m.group("G").upper()))
        elif m.group("AND") is not None:
            toks.append(("AND", None))
        elif m.group("OR") is not None:
            toks.append(("OR", None))
        elif m.group("COURSE") is not None:
            toks.append(("COURSE", m.group("COURSE").upper()))
    return toks


class _Parser:
    def __init__(self, toks: list[tuple[str, Optional[str]]]):
        self.toks = toks
        self.i = 0

    def _peek(self) -> tuple[Optional[str], Optional[str]]:
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def _next(self) -> tuple[Optional[str], Optional[str]]:
        t = self._peek()
        self.i += 1
        return t

    def parse(self) -> PrereqExpr:
        expr = self._or()
        if self.i != len(self.toks):
            raise PrereqParseError("trailing tokens after complete expression")
        return expr

    def _or(self) -> PrereqExpr:
        nodes = [self._and()]
        while self._peek()[0] == "OR":
            self._next()
            nodes.append(self._and())
        return nodes[0] if len(nodes) == 1 else Or(children=nodes)

    def _and(self) -> PrereqExpr:
        nodes = [self._factor()]
        while self._peek()[0] == "AND":
            self._next()
            nodes.append(self._factor())
        return nodes[0] if len(nodes) == 1 else And(children=nodes)

    def _factor(self) -> PrereqExpr:
        kind, val = self._peek()
        if kind == "LP":
            self._next()
            expr = self._or()
            if self._peek()[0] != "RP":
                raise PrereqParseError("expected ')'")
            self._next()
            return expr
        if kind == "COURSE":
            self._next()
            min_grade = None
            if self._peek()[0] == "GRADE":
                min_grade = self._next()[1]
            return Atom(course=val, min_grade=min_grade)
        raise PrereqParseError(f"unexpected token {kind!r}")


def parse_prereqs(text: Optional[str]) -> Optional[PrereqExpr]:
    """Parse prerequisite text into an AST, or ``None`` if empty/unparseable."""
    if not text or not text.strip():
        return None
    try:
        toks = _tokenize(text)
        if not toks:
            return None
        return _Parser(toks).parse()
    except PrereqParseError:
        return None
