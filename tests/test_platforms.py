"""What holds Gadfly alike on Linux, macOS and Windows, read from the source."""

import ast
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCES = sorted(
    path
    for folder in ("midwife", "tools", "tests", "examples")
    for path in (ROOT / folder).rglob("*.py")
    if "runs" not in path.relative_to(ROOT).parts
)
SUBPROCESS = {"run", "Popen", "check_output", "check_call", "call"}


def _unnamed(call: ast.Call) -> bool:
    """A text file or a child's text opened with no encoding: before Python
    3.15 Windows reads and writes it in its code page, not UTF-8."""
    named = {keyword.arg for keyword in call.keywords}
    if "encoding" in named or None in named:  # named, or passed on in **options
        return False
    func = call.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
    mode = next((k.value for k in call.keywords if k.arg == "mode"), None)
    if name == "read_text":
        return not call.args
    if name in ("write_text", "TextIOWrapper"):  # each takes its encoding second
        return len(call.args) < 2
    if name == "open" and isinstance(func, ast.Name):  # open(file, mode, buffering, encoding)
        mode = mode or (call.args[1] if len(call.args) > 1 else None)
        return len(call.args) < 4 and "b" not in getattr(mode, "value", "")
    if name == "open":  # a path's open(mode): a URL opener's open(request) is not a file
        mode = mode or (call.args[0] if call.args else ast.Constant(""))
        return isinstance(mode, ast.Constant) and "b" not in str(mode.value)
    if name in SUBPROCESS:
        texts = [k.value for k in call.keywords if k.arg in ("text", "universal_newlines")]
        return any(getattr(text, "value", True) for text in texts)
    return False


def test_every_text_file_and_child_names_its_encoding():
    unnamed = [
        f"{path.relative_to(ROOT).as_posix()}:{node.lineno}"
        for path in SOURCES
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and _unnamed(node)
    ]
    assert unnamed == []
