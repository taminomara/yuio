import pytest
import yuio.term


class TestColor:
    @pytest.mark.parametrize(
        "color,cap,expect",
        [
            (yuio.term.Color.NONE, yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.NONE, yuio.term.ColorSupport.ANSI, "\x1b[m"),
            (yuio.term.Color.NONE, yuio.term.ColorSupport.ANSI_256, "\x1b[m"),
            (yuio.term.Color.NONE, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[m"),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.ANSI, "\x1b[;31m"),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.ANSI_256, "\x1b[;31m"),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;31m"),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.ANSI, "\x1b[;41m"),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.ANSI_256, "\x1b[;41m"),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;41m"),
            (yuio.term.Color.fore_from_hex("#338F15"), yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.fore_from_hex("#338F15"), yuio.term.ColorSupport.ANSI, "\x1b[;32m"),
            (yuio.term.Color.fore_from_hex("#338F15"), yuio.term.ColorSupport.ANSI_256, "\x1b[;38;5;64m"),
            (yuio.term.Color.fore_from_hex("#338F15"), yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;38;2;51;143;21m"),
            (yuio.term.Color.back_from_hex("#338F15"), yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.back_from_hex("#338F15"), yuio.term.ColorSupport.ANSI, "\x1b[;42m"),
            (yuio.term.Color.back_from_hex("#338F15"), yuio.term.ColorSupport.ANSI_256, "\x1b[;48;5;64m"),
            (yuio.term.Color.back_from_hex("#338F15"), yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;48;2;51;143;21m"),
        ]
    )
    def test_as_code(self, color: yuio.term.Color, cap, expect):
        term = yuio.term.Term(None, color_support=cap)  # type: ignore
        assert color.as_code(term) == expect

    @pytest.mark.parametrize(
        "colors,coeffs,expect",
        [
            (
                [yuio.term.Color.FORE_RED, yuio.term.Color.FORE_GREEN],
                [i / 4 for i in range(5)],
                [yuio.term.Color.FORE_RED] * 5,
            ),
            (
                [yuio.term.Color.FORE_RED, yuio.term.Color.fore_from_hex("#AA0000")],
                [i / 4 for i in range(5)],
                [yuio.term.Color.FORE_RED] * 5,
            ),
            (
                [yuio.term.Color.fore_from_hex("#AA0000"), yuio.term.Color.FORE_RED],
                [i / 4 for i in range(5)],
                [yuio.term.Color.fore_from_hex("#AA0000")] * 5,
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ],
                [i / 4 for i in range(5)],
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#7F2A00"),
                    yuio.term.Color.fore_from_hex("#555500"),
                    yuio.term.Color.fore_from_hex("#2A7F00"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ]
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                    yuio.term.Color.fore_from_hex("#0000AA"),
                ],
                [i / 8 for i in range(9)],
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#7F2A00"),
                    yuio.term.Color.fore_from_hex("#555500"),
                    yuio.term.Color.fore_from_hex("#2A7F00"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                    yuio.term.Color.fore_from_hex("#007F2A"),
                    yuio.term.Color.fore_from_hex("#005555"),
                    yuio.term.Color.fore_from_hex("#002A7F"),
                    yuio.term.Color.fore_from_hex("#0000AA"),
                ]
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ],
                [0, 0.5, 1],
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#555500"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ]
            ),
            (
                [
                    yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.back_from_hex("#00AA00"),
                ],
                [0, 0.5, 1],
                [
                    yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.back_from_hex("#005555"),
                    yuio.term.Color.back_from_hex("#00AA00"),
                ]
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000") | yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.fore_from_hex("#00AA00") | yuio.term.Color.back_from_hex("#00AA00"),
                ],
                [0, 0.5, 1],
                [
                    yuio.term.Color.fore_from_hex("#AA0000") | yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.fore_from_hex("#555500") | yuio.term.Color.back_from_hex("#005555"),
                    yuio.term.Color.fore_from_hex("#00AA00") | yuio.term.Color.back_from_hex("#00AA00"),
                ]
            ),
        ]
    )
    def test_lerp(self, colors, coeffs, expect):
        lerp = yuio.term.Color.lerp(*colors)
        result = [lerp(c) for c in coeffs]
        assert result == expect


class TestTheme:
    def test_default_colors(self):
        t = yuio.term.Theme()

        assert t.get_color('code') == yuio.term.Color.FORE_MAGENTA
        assert t.get_color('note') == yuio.term.Color.FORE_GREEN
        assert t.get_color('bold') == yuio.term.Color.STYLE_BOLD
        assert t.get_color('b') == yuio.term.Color.STYLE_BOLD
        assert t.get_color('dim') == yuio.term.Color.STYLE_DIM
        assert t.get_color('d') == yuio.term.Color.STYLE_DIM
        assert t.get_color('normal') == yuio.term.Color.FORE_NORMAL
        assert t.get_color('black') == yuio.term.Color.FORE_BLACK
        assert t.get_color('red') == yuio.term.Color.FORE_RED
        assert t.get_color('green') == yuio.term.Color.FORE_GREEN
        assert t.get_color('yellow') == yuio.term.Color.FORE_YELLOW
        assert t.get_color('blue') == yuio.term.Color.FORE_BLUE
        assert t.get_color('magenta') == yuio.term.Color.FORE_MAGENTA
        assert t.get_color('cyan') == yuio.term.Color.FORE_CYAN
        assert t.get_color('white') == yuio.term.Color.FORE_WHITE

    def test_inheritance(self):
        class A(yuio.term.Theme):
            colors = {
                't_a': yuio.term.Color.FORE_RED,
                't_ab': yuio.term.Color.FORE_GREEN,
                't_abc': yuio.term.Color.FORE_BLUE,
            }

        class B(yuio.term.Theme):
            colors = {
                't_b': yuio.term.Color.FORE_CYAN,
                't_ab': yuio.term.Color.FORE_MAGENTA,
                't_abc': yuio.term.Color.FORE_YELLOW,
            }

        class C(A, B):
            colors = {
                't_c': yuio.term.Color.FORE_BLACK,
                't_abc': yuio.term.Color.FORE_WHITE,
            }

        assert C.colors['t_a'] == yuio.term.Color.FORE_RED
        assert C.colors['t_b'] == yuio.term.Color.FORE_CYAN
        assert C.colors['t_c'] == yuio.term.Color.FORE_BLACK
        assert C.colors['t_ab'] == yuio.term.Color.FORE_GREEN
        assert C.colors['t_abc'] == yuio.term.Color.FORE_WHITE

        c = C()

        assert c.get_color('t_a') == yuio.term.Color.FORE_RED
        assert c.get_color('t_b') == yuio.term.Color.FORE_CYAN
        assert c.get_color('t_c') == yuio.term.Color.FORE_BLACK
        assert c.get_color('t_ab') == yuio.term.Color.FORE_GREEN
        assert c.get_color('t_abc') == yuio.term.Color.FORE_WHITE

    def test_color_paths(self):
        class A(yuio.term.Theme):
            colors = {
                'x': yuio.term.Color.STYLE_BOLD,
                'x/y': yuio.term.Color.FORE_RED,
                'x/z': yuio.term.Color.FORE_GREEN,
                'y/y': yuio.term.Color.FORE_BLUE,
            }

        a = A()

        assert a.get_color('x') == yuio.term.Color.STYLE_BOLD
        assert a.get_color('x/y') == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED
        assert a.get_color('x/z') == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_GREEN
        assert a.get_color('y/y') == yuio.term.Color.FORE_BLUE

    def test_color_redirect(self):
        class A(yuio.term.Theme):
            colors = {
                't_r': yuio.term.Color.FORE_RED,
                't_g': yuio.term.Color.FORE_GREEN,
                't_b': yuio.term.Color.STYLE_BOLD,
                't_d': yuio.term.Color.STYLE_DIM,

                'x': 't_b',
                'x/y': 't_r',

                'y': 't_d',
                'y/y': 'x/y',

                'z': ['x/y', 'y/y', yuio.term.Color.BACK_CYAN]
            }

        a = A()

        assert a.get_color('x') == yuio.term.Color.STYLE_BOLD
        assert a.get_color('x/y') == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED
        assert a.get_color('y') == yuio.term.Color.STYLE_DIM
        assert a.get_color('y/y') == yuio.term.Color.STYLE_DIM | yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED
        assert a.get_color('z') == yuio.term.Color.STYLE_DIM | yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED | yuio.term.Color.BACK_CYAN


class TestColorizedString:
    @pytest.mark.parametrize(
        "text,args,expect",
        [
            (
                [""], (),
                [""],
            ),
            (
                ["hello world!"], (),
                ["hello world!"],
            ),
            (
                ["hello %s!"], "username",
                ["hello username!"],
            ),
            (
                ["hello %r!"], "username",
                ["hello 'username'!"],
            ),
            (
                ["hello %05.2f!"], 1.5,
                ["hello 01.50!"],
            ),
            (
                ["hello %05.2lf!"], 1.5,
                ["hello 01.50!"],
            ),
            (
                ["hello %s %% %s!"], (1, 2),
                ["hello 1 % 2!"],
            ),
            (
                ["hello %s"], {'a': 'b'},
                ["hello {'a': 'b'}"],
            ),
            (
                ["hello %s %(a)s"], {'a': 'b'},
                ["hello {'a': 'b'} b"],
            ),
        ]
    )
    def test_format(self, text, args, expect):
        formatted = yuio.term.ColorizedString(text) % args
        assert formatted._items == expect

    @pytest.mark.parametrize(
        "text,width,kwargs,expect",
        [
            (
                ["hello world!"], 15, {},
                [["hello", " ", "world!"]]
            ),
            (
                ["hello world! 15"], 15, {},
                [["hello", " ", "world!", " ", "15"]]
            ),
            (
                ["hello world! 👻"], 15, {},
                [["hello", " ", "world!", " ", "👻"]]
            ),
            (
                ["hello world! 👻👻"], 15, {},
                [["hello", " ", "world!"], ["👻👻"]]
            ),
            (
                ["hello world! this will wrap"], 15, {},
                [["hello", " ", "world!"], ["this", " ", "will", " ", "wrap"]]
            ),
            (
                ["hello world!     this will wrap"], 15, {},
                [["hello", " ", "world!"], ["this", " ", "will", " ", "wrap"]]
            ),
            (
                ["hello     world!     this     will     wrap"], 15, {},
                [["hello", " ", "world!"], ["this", " ", "will", " ", "wrap"]]
            ),
            (
                ["this-will-wrap-on-hyphen"], 15, {},
                [["this-", "will-", "wrap-"], ["on-", "hyphen"]]
            ),
            (
                ["this.will.not.wrap.on.hyphen.this.is.too.long"], 15, {},
                [["this.will.not.w"], ["rap.on.hyphen.t"], ["his.is.too.long"]]
            ),
            (
                ["this-will-not-wrap-on-hyphen-this-is-too-long"], 15, {'break_on_hyphens': False},
                [["this-will-not-w"], ["rap-on-hyphen-t"], ["his-is-too-long"]]
            ),
            (
                ["newlines will\nbe\nhonored!"], 15, {'break_on_hyphens': False},
                [["newlines", " ", "will"], ["be"], ["honored!"]]
            ),
            (
                ["space before nl    \nis removed"], 15, {},
                [["space", " ", "before", " ", "nl"], ["is", " ", "removed"]]
            ),
            (
                ["space after nl\n    is kept"], 15, {},
                [["space", " ", "after", " ", "nl"], ["    ", "is", " ", "kept"]]
            ),
            (
                ["wo", "rd wo", "rd"], 15, {},
                [["wo", "rd", " ", "wo", "rd"]],
            ),
            pytest.param(
                ["wo", "rd wo", "rd"], 7, {},
                [["wo", "rd"], ["wo", "rd"]],
                marks=pytest.mark.skip("this is a bug which I'm not sure how to fix atm"),
            ),
            (
                ["hello world!"], 15, {'preserve_spaces': True},
                [["hello", " ", "world!"]]
            ),
            (
                ["hello   world!"], 15, {'preserve_spaces': True},
                [["hello", "   ", "world!"]]
            ),
            (
                ["hello     world!"], 15, {'preserve_spaces': True},
                [["hello", "     "], ["world!"]]
            ),
            (
                ["hello                    world"], 15, {'preserve_spaces': True},
                [["hello", "          "], ["          ", "world"]]
            ),
            (
                ["hello                    longlongworld"], 15, {'preserve_spaces': True},
                [["hello", "          "], ["          "], ["longlongworld"]]
            ),
            (
                ["hello ", yuio.term.Color.STYLE_BOLD, "world", yuio.term.Color.NONE], 15, {'preserve_spaces': True},
                [["hello", " ", yuio.term.Color.STYLE_BOLD, "world", yuio.term.Color.NONE]]
            ),
            (
                [], 15, {'preserve_spaces': True},
                [[]]
            ),
            (
                [""], 15, {'preserve_spaces': True},
                [[]]
            ),
            (
                ["Hello line break", yuio.term.Color.NONE], 15, {},
                [["Hello", " ", "line"], ["break", yuio.term.Color.NONE]]
            ),
            (
                [yuio.term.Color.STYLE_BOLD, yuio.term.Color.NONE], 15, {},
                [[yuio.term.Color.STYLE_BOLD, yuio.term.Color.NONE]]
            ),
            (
                [yuio.term.Color.STYLE_BOLD, "", yuio.term.Color.NONE], 15, {},
                [[yuio.term.Color.STYLE_BOLD, yuio.term.Color.NONE]]
            ),
            (
                ["break\n", yuio.term.Color.NONE], 15, {},
                [["break"], [yuio.term.Color.NONE]]
            ),
            (
                ["break\n"], 15, {},
                [["break"], []]
            ),
            (
                ["usage: app.py train [-h] [-v] [--force-color | --force-no-color] [-o {path}] <data>"], 100, {},
                [['usage:', ' ', 'app.py', ' ', 'train', ' ', '[-h]', ' ', '[-v]', ' ',
                  '[--force-', 'color', ' ', '|', ' ', '--force-', 'no-', 'color]', ' ',
                  '[-o', ' ', '{path}]', ' ', '<data>']]
            ),
            (
                [
                    yuio.term.Color.FORE_MAGENTA, 'usage: ', yuio.term.Color.NONE, yuio.term.Color.NONE, 'app.py train', yuio.term.Color.NONE, yuio.term.Color.NONE, ' ', yuio.term.Color.NONE, '[', yuio.term.Color.FORE_BLUE, '-h', yuio.term.Color.NONE, ']', yuio.term.Color.NONE, ' ', yuio.term.Color.NONE, '[', yuio.term.Color.FORE_BLUE, '-v', yuio.term.Color.NONE, ']', yuio.term.Color.NONE, ' [', yuio.term.Color.NONE, yuio.term.Color.FORE_BLUE, '--force-color', yuio.term.Color.NONE, ' | ', yuio.term.Color.NONE, yuio.term.Color.FORE_BLUE, '--force-no-color', yuio.term.Color.NONE, '] ', yuio.term.Color.NONE, '[', yuio.term.Color.FORE_BLUE, '-o', yuio.term.Color.NONE, ' ', yuio.term.Color.FORE_MAGENTA, '', yuio.term.Color.NONE, '{', yuio.term.Color.FORE_MAGENTA, 'path', yuio.term.Color.NONE, '}', yuio.term.Color.FORE_MAGENTA, '', yuio.term.Color.NONE, ']', yuio.term.Color.NONE, ' ', yuio.term.Color.NONE, yuio.term.Color.FORE_MAGENTA, '', yuio.term.Color.NONE, '<', yuio.term.Color.FORE_MAGENTA, 'data', yuio.term.Color.NONE, '>', yuio.term.Color.FORE_MAGENTA, ''], 100, {},
                [['usage:', ' ', 'app.py', ' ', 'train', ' ', '[-h]', ' ', '[-v]', ' ',
                  '[--force-', 'color', ' ', '|', ' ', '--force-', 'no-', 'color]', ' ',
                  '[-o', ' ', '{path}]', ' ', '<data>']]
            ),
        ]
    )
    def test_wrap(self, text, width, kwargs, expect):
        wrapped = yuio.term.ColorizedString(text).wrap(width, **kwargs)
        raw = [line._items for line in wrapped]
        assert raw == expect

    def test_wrap_err(self):
        with pytest.raises(ValueError, match="width"):
            yuio.term.ColorizedString("").wrap(1)
        with pytest.raises(ValueError, match="width"):
            yuio.term.ColorizedString("").wrap(0)
        with pytest.raises(ValueError, match="width"):
            yuio.term.ColorizedString("").wrap(-1)
