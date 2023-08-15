import abc
import enum
import re
import textwrap
import typing as _t


_TO_DASH_CASE_RE = re.compile(
    r'(?<!^)((?=[A-Z]([^A-Z]|$))|(?<=\d)(?=[A-Z])|(?<!\d)(?=\d))'
)


def to_dash_case(s: str) -> str:
    return _TO_DASH_CASE_RE.sub('-', s).lower()


_COMMENT_RE = re.compile(r'^\s*#:(.*)\r?\n?$')


def find_docs(obj: _t.Any) -> _t.Dict[str, str]:
    # based on code from Sphinx

    import inspect
    import itertools
    import ast

    if '<locals>' in obj.__qualname__:
        # This will not work as expected!
        return {}

    sourcelines, _ = inspect.getsourcelines(obj)

    docs = {}

    node = ast.parse(textwrap.dedent(''.join(sourcelines)))
    assert isinstance(node, ast.Module)
    assert len(node.body) == 1
    cdef = node.body[0]

    if isinstance(cdef, ast.ClassDef):
        fields = [
            (stmt.lineno, stmt.target.id)
            for stmt in cdef.body
            if (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and not stmt.target.id.startswith('_')
            )
        ]
    elif isinstance(cdef, ast.FunctionDef):
        fields = [
            (field.lineno, field.arg)
            for field in
            itertools.chain(cdef.args.args, cdef.args.kwonlyargs)
        ]
    else:
        return {}

    for (pos, name) in fields:
        comment_lines = []
        for before_line in sourcelines[pos - 2::-1]:
            if match := _COMMENT_RE.match(before_line):
                comment_lines.append(match.group(1))
            else:
                break

        if comment_lines:
            docs[name] = textwrap.dedent('\n'.join(reversed(comment_lines)))

    return docs
