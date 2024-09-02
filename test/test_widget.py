import io

import yuio.term
import yuio.theme
import yuio.widget

from .conftest import RcCompare


class TestRenderContext:
    def test_write_no_colors(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar!             ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
