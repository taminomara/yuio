import os
import re
import subprocess
import tempfile
import typing as _t


def detect_editor() -> _t.Optional[str]:
    if 'EDITOR' in os.environ:
        return os.environ['EDITOR']
    elif (
        subprocess.run(
            ['which', 'nano'], stdout=subprocess.DEVNULL
        ).returncode == 0
    ):
        return 'nano'
    elif (
        subprocess.run(
            ['which', 'vi'], stdout=subprocess.DEVNULL
        ).returncode == 0
    ):
        return 'vi'
    else:
        return None


def edit(
    text: str,
    comment_marker: _t.Optional[str] = '#'
) -> str:
    editor = detect_editor()
    if editor is None:
        raise RuntimeError(
            'can\'t detect an editor, ensure that the $EDITOR environment z'
            'variable contains a correct path to an editor executable'
        )

    filepath = tempfile.mktemp()
    with open(filepath, 'w') as file:
        file.write(text)

    try:
        try:
            res = subprocess.run([editor, filepath])
        except FileNotFoundError:
            raise RuntimeError(
                'can\'t use this editor, ensure that the $EDITOR environment '
                'variable contains a correct path to an editor executable'
            )

        if res.returncode != 0:
            raise RuntimeError(
                'editing failed'
            )

        with open(filepath, 'r') as file:
            text = file.read()

        if comment_marker is not None:
            text = re.sub(
                r'^\s*' + re.escape(comment_marker) + r'.*\n',
                '',
                text,
                flags=re.MULTILINE
            )

        return text.strip()
    finally:
        os.remove(filepath)
