"""Tokenizer for the supported Fortran subset (free-form source).

Handles: line comments ('!'), line continuation ('&' at end of line, optional
'&' at start of continuation), case-insensitivity, the dotted relational /
logical operators (.EQ. .LT. .AND. ...), and string literals in both quote
styles.
"""

from dataclasses import dataclass


class LexError(Exception):
    pass


@dataclass
class Token:
    kind: str       # e.g. 'ID', 'INT', 'REAL', 'STR', 'NEWLINE', 'EOF', or a literal like '+', '::'
    value: object
    line: int

    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r}, line={self.line})"


KEYWORDS = {
    "PROGRAM", "END", "SUBROUTINE", "FUNCTION", "RETURN", "CONTAINS",
    "INTEGER", "REAL", "DOUBLE", "PRECISION", "LOGICAL", "CHARACTER",
    "DIMENSION", "IMPLICIT", "NONE", "PARAMETER", "INTENT", "IN", "OUT", "INOUT",
    "CALL", "IF", "THEN", "ELSE", "ENDIF", "DO", "ENDDO", "WHILE",
    "EXIT", "CYCLE", "STOP", "CONTINUE",
    "PRINT", "WRITE", "READ",
    "EXTERNAL", "RECURSIVE", "BIND",
}

# dotted operators, longest first so .EQV. isn't cut short by .EQ.
DOTTED_OPS = [
    ".TRUE.", ".FALSE.",
    ".NEQV.", ".EQV.",
    ".AND.", ".OR.", ".NOT.",
    ".EQ.", ".NE.", ".LT.", ".LE.", ".GT.", ".GE.",
]

SYMBOLS = [
    "::", "**", "==", "/=", "//", "<=", ">=",
    "(", ")", ",", "=", "+", "-", "*", "/", "<", ">", ":",
]


def tokenize(source: str):
    tokens = []
    line_no = 0
    lines = source.split("\n")

    # join continuation lines first
    logical_lines = []
    buf = ""
    buf_start_line = 1
    for raw in lines:
        line_no += 1
        line = raw
        # strip comments (but not '!' inside quotes)
        line = _strip_comment(line)
        stripped = line.strip()
        if buf == "":
            buf_start_line = line_no
        if stripped.startswith("&"):
            stripped = stripped[1:].lstrip()
        if stripped.endswith("&"):
            buf += stripped[:-1].rstrip() + " "
            continue
        buf += stripped
        logical_lines.append((buf_start_line, buf))
        buf = ""
    if buf:
        logical_lines.append((buf_start_line, buf))

    for lno, text in logical_lines:
        if text.strip() == "":
            continue
        tokens.extend(_tokenize_line(text, lno))
        tokens.append(Token("NEWLINE", None, lno))

    tokens.append(Token("EOF", None, line_no + 1))
    return tokens


def _strip_comment(line: str) -> str:
    in_squote = False
    in_dquote = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_dquote:
            in_squote = not in_squote
        elif ch == '"' and not in_squote:
            in_dquote = not in_dquote
        elif ch == "!" and not in_squote and not in_dquote:
            return line[:i]
    return line


def _tokenize_line(text: str, lno: int):
    toks = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t":
            i += 1
            continue
        if ch == "'" or ch == '"':
            quote = ch
            j = i + 1
            s = []
            while j < n:
                if text[j] == quote:
                    if j + 1 < n and text[j + 1] == quote:
                        s.append(quote)
                        j += 2
                        continue
                    break
                s.append(text[j])
                j += 1
            if j >= n:
                raise LexError(f"line {lno}: unterminated string literal")
            toks.append(Token("STR", "".join(s), lno))
            i = j + 1
            continue
        if ch == "." and _peek_dotted(text, i):
            for op in DOTTED_OPS:
                if text[i:i + len(op)].upper() == op:
                    if op in (".TRUE.", ".FALSE."):
                        toks.append(Token("BOOL", op == ".TRUE.", lno))
                    else:
                        toks.append(Token(op, op, lno))
                    i += len(op)
                    break
            else:
                raise LexError(f"line {lno}: unrecognized '.' operator near {text[i:i+8]!r}")
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and text[i + 1].isdigit()):
            j = i
            is_real = False
            while j < n and text[j].isdigit():
                j += 1
            if j < n and text[j] == ".":
                is_real = True
                j += 1
                while j < n and text[j].isdigit():
                    j += 1
            if j < n and text[j] in "eEdD" and (j + 1 < n and (text[j+1].isdigit() or text[j+1] in "+-")):
                is_real = True
                j += 1
                if text[j] in "+-":
                    j += 1
                while j < n and text[j].isdigit():
                    j += 1
            lit = text[i:j].replace("d", "e").replace("D", "e")
            if is_real:
                toks.append(Token("REAL", float(lit), lno))
            else:
                toks.append(Token("INT", int(lit), lno))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            upper = word.upper()
            if upper in KEYWORDS:
                toks.append(Token(upper, upper, lno))
            else:
                toks.append(Token("ID", word.lower(), lno))
            i = j
            continue
        matched = False
        for sym in SYMBOLS:
            if text[i:i + len(sym)] == sym:
                toks.append(Token(sym, sym, lno))
                i += len(sym)
                matched = True
                break
        if matched:
            continue
        raise LexError(f"line {lno}: unexpected character {ch!r}")
    return toks


def _peek_dotted(text: str, i: int) -> bool:
    return any(text[i:i + len(op)].upper() == op for op in DOTTED_OPS)
