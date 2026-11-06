"""A small HCL text scanner for static checks and mutation edits (stdlib only; not an HCL parser).

It understands comments, quoted strings with ${...} interpolation (including nested quotes) and heredocs, which is
enough to enumerate `resource` blocks, find a block's matching brace, and delete one attribute for a mutation case.
"""
import re

_HEREDOC = re.compile(r"<<-?([A-Za-z_][A-Za-z_0-9]*)[ \t]*\n")


def _skip_string(text, i):
    """text[i] == '"'; return the index just after the closing quote."""
    i += 1
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i + 1
        if c in "$%" and text[i + 1:i + 2] == "{" and text[i - 1:i] != c:
            i = _skip_interpolation(text, i + 2)
            continue
        i += 1
    return i


def _skip_interpolation(text, i):
    depth = 1
    while i < len(text):
        c = text[i]
        if c == '"':
            i = _skip_string(text, i)
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _skip_heredoc(text, i):
    m = _HEREDOC.match(text, i)
    if not m:
        return None
    end = re.compile(r"^[ \t]*" + re.escape(m.group(1)) + r"[ \t]*$", re.M).search(text, m.end())
    return end.end() if end else len(text)


def _skip_comment(text, i):
    if text.startswith(("#", "//"), i):
        nl = text.find("\n", i)
        return len(text) if nl < 0 else nl
    if text.startswith("/*", i):
        end = text.find("*/", i + 2)
        return len(text) if end < 0 else end + 2
    return None


def strip_comments(text):
    """The text with comments blanked out (line structure kept), so literals in prose are never matched."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        skipped = _skip_comment(text, i)
        if skipped is not None:
            out.append(re.sub(r"[^\n]", " ", text[i:skipped]))
            i = skipped
        elif c == '"':
            j = _skip_string(text, i)
            out.append(text[i:j])
            i = j
        elif text.startswith("<<", i) and _skip_heredoc(text, i) is not None:
            j = _skip_heredoc(text, i)
            out.append(text[i:j])
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def matching_brace(text, open_index):
    """Index of the `}` that closes the `{` at open_index (comments assumed already stripped)."""
    assert text[open_index] == "{"
    depth, i = 0, open_index
    while i < len(text):
        c = text[i]
        if c == '"':
            i = _skip_string(text, i)
            continue
        if text.startswith("<<", i):
            j = _skip_heredoc(text, i)
            if j is not None:
                i = j
                continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced braces")


_RESOURCE = re.compile(r'^[ \t]*resource[ \t]+"([A-Za-z0-9_]+)"[ \t]+"([A-Za-z0-9_-]+)"[ \t]*\{', re.M)


def resource_blocks(text):
    """[(type, name, body)] for every top-level-looking `resource "t" "n" {` block of comment-stripped text."""
    clean = strip_comments(text)
    blocks = []
    for m in _RESOURCE.finditer(clean):
        end = matching_brace(clean, m.end() - 1)
        blocks.append((m.group(1), m.group(2), clean[m.end():end]))
    return blocks


def value_end(text, i):
    """Index of the newline that ends the attribute value starting at i (brackets and strings balanced)."""
    depth = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            i = _skip_string(text, i)
            continue
        if text.startswith("<<", i):
            j = _skip_heredoc(text, i)
            if j is not None:
                i = j
                continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif c == "\n" and depth <= 0:
            return i
        i += 1
    return len(text)


def strip_attribute_after(text, anchor, attribute):
    """Delete `attribute = <value>` (balanced, possibly multi-line) that first follows `anchor`; returns new text."""
    a = text.find(anchor)
    if a < 0:
        raise KeyError("anchor not found: %r" % anchor)
    m = re.compile(r"^[ \t]*" + re.escape(attribute) + r"[ \t]*=[ \t]*", re.M).search(text, a)
    if not m:
        raise KeyError("attribute %r not found after anchor %r" % (attribute, anchor))
    return text[:m.start()] + text[value_end(text, m.end()) + 1:]


def smallest_object_containing(text, needle):
    """The text of the innermost `{ ... }` of comment-stripped text that contains `needle` (None when absent)."""
    clean = strip_comments(text)
    index = clean.find(needle)
    if index < 0:
        return None
    best = None
    for i, ch in enumerate(clean):
        if ch == "{" and i < index:
            try:
                end = matching_brace(clean, i)
            except ValueError:
                continue
            if end > index and (best is None or end - i < best[1] - best[0]):
                best = (i, end)
    return None if best is None else clean[best[0]:best[1] + 1]
