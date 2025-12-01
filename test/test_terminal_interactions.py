import os
import pathlib
import sys
import time

import pytest
from libtmux.pane import Pane
from libtmux.server import Server


@pytest.fixture
def python_path():
    return pathlib.Path(sys.executable)


@pytest.fixture
def pane(server: Server):
    session = server.new_session()
    for k, v in os.environ.items():
        if k.startswith("COV"):
            session.set_environment(k, v)
    window = session.new_window(window_shell="bash")
    pane = window.active_pane
    assert pane is not None
    return pane


@pytest.mark.linux
@pytest.mark.full
@pytest.mark.flaky
def test_tmux(pane: Pane, tmp_path, python_path):
    output_path = tmp_path / "output.txt"
    pane.send_keys("pwd")
    pane.send_keys(
        f"{python_path} -m yuio.scripts.showkey --modify-keyboard > {output_path}"
    )
    time.sleep(2)
    pane.send_keys("abc")
    keys = [
        "Escape",
        "Up",
        "Down",
        "Left",
        "Right",
        "Home",
        "End",
        "PageUp",
        "PageDown",
        "Insert",
        "Delete",
        "BSpace",
        "Tab",
        "BTab",
        "Space",
    ]
    prefixes = [
        "",
        "^",
        "M-",
        "^M-",
    ]
    for key in keys:
        for prefix in prefixes:
            pane.send_keys(prefix + key, enter=False)
    pane.send_keys("C-d", enter=False)
    pane.send_keys("C-5", enter=False)
    pane.send_keys("C-_", enter=False)
    pane.send_keys("C-c", enter=False)
    print("-" * 80)
    print("\n".join(pane.capture_pane()))
    print("-" * 80)
    pane.kill()
    result = output_path.read_text()
    print(result)
    assert result == EXPECTED


EXPECTED = r"""
Key: 'a'
Key: 'b'
Key: 'c'
Key: ENTER
Key: ESCAPE
Key: Ctrl+ESCAPE
Key: Alt+ESCAPE
Key: Ctrl+Alt+ESCAPE
Key: ARROW_UP
Key: Ctrl+ARROW_UP
Key: Alt+ARROW_UP
Key: Ctrl+Alt+ARROW_UP
Key: ARROW_DOWN
Key: Ctrl+ARROW_DOWN
Key: Alt+ARROW_DOWN
Key: Ctrl+Alt+ARROW_DOWN
Key: ARROW_LEFT
Key: Ctrl+ARROW_LEFT
Key: Alt+ARROW_LEFT
Key: Ctrl+Alt+ARROW_LEFT
Key: ARROW_RIGHT
Key: Ctrl+ARROW_RIGHT
Key: Alt+ARROW_RIGHT
Key: Ctrl+Alt+ARROW_RIGHT
Key: HOME
Key: Ctrl+HOME
Key: Alt+HOME
Key: Ctrl+Alt+HOME
Key: END
Key: Ctrl+END
Key: Alt+END
Key: Ctrl+Alt+END
Key: PAGE_UP
Key: Ctrl+PAGE_UP
Key: Alt+PAGE_UP
Key: Ctrl+Alt+PAGE_UP
Key: PAGE_DOWN
Key: Ctrl+PAGE_DOWN
Key: Alt+PAGE_DOWN
Key: Ctrl+Alt+PAGE_DOWN
Key: INSERT
Key: Ctrl+INSERT
Key: Alt+INSERT
Key: Ctrl+Alt+INSERT
Key: DELETE
Key: Ctrl+DELETE
Key: Alt+DELETE
Key: Ctrl+Alt+DELETE
Key: BACKSPACE
Key: Ctrl+BACKSPACE
Key: Alt+BACKSPACE
Key: Ctrl+Alt+BACKSPACE
Key: TAB
Key: Ctrl+TAB
Key: Alt+TAB
Key: Alt+TAB
Key: Shift+TAB
Key: Ctrl+'\U0010e1a7'
Key: Shift+Alt+TAB
Key: Ctrl+Alt+'\U0010e1a7'
Key: ' '
Key: Ctrl+'`'
Key: Alt+' '
Key: Ctrl+Alt+'`'
Key: Ctrl+'d'
Key: Ctrl+'5'
Key: Ctrl+'7'
""".lstrip()
