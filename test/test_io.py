import io

import pytest

import yuio.io
from yuio.io import *


class AttyStream(io.StringIO):
    def __init__(self, atty:bool):
        super().__init__()
        self.atty = atty

    def isatty(self):
        return self.atty


@pytest.fixture
def stream():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    yield stream

    setup()


@pytest.fixture
def stream_no_color():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    yield stream

    setup()


@pytest.fixture
def stream_interactive(save_env):
    os.environ['TERM'] = 'xterm-256color'

    stream = AttyStream(True)
    setup(use_colors=True, level=DEBUG, stream=stream)

    yield stream

    setup()


@pytest.fixture(autouse=True)
def reset_logging():
    yuio.io._HANDLER_IMPL._tasks = []
    yuio.io._HANDLER_IMPL._tasks_shown = 0
    yuio.io._HANDLER_IMPL._suspended = 0
    yuio.io._HANDLER_IMPL._suspended_lines = []

    yield

    assert yuio.io._HANDLER_IMPL._tasks == []
    assert yuio.io._HANDLER_IMPL._tasks_shown == 0
    assert yuio.io._HANDLER_IMPL._suspended == 0
    assert yuio.io._HANDLER_IMPL._suspended_lines == []


class TestColor:
    def test_output(self):
        assert str(Color()) == '\033[0m'
        assert str(Color(31)) == '\033[0;31m'
        assert str(Color(32, bold=True, dim=True)) == '\033[0;32;1;2m'
        assert str(Color(bold=True)) == '\033[0;1m'

    def test_combine(self):
        assert Color(1) | Color(2) == Color(2)
        assert Color(1) | Color() == Color(1)
        assert Color() | Color(1) == Color(1)
        assert Color(1) | Color(bold=True) == Color(1, bold=True)
        assert Color(1, bold=True) | Color(2) == Color(2, bold=True)


class TestHelpers:
    def test_detect_editor(self, save_env):
        os.environ['EDITOR'] = 'subl'

        assert detect_editor() == 'subl'

    def test_is_interactive(self, save_env):
        os.environ['TERM'] = 'xterm-256color'

        setup(stream=AttyStream(True))  # type: ignore
        assert is_interactive()

        setup(stream=AttyStream(False))  # type: ignore
        assert not is_interactive()

        os.environ['TERM'] = 'dumb'
        setup(stream=AttyStream(True))  # type: ignore
        assert not is_interactive()


class TestLoggingNoColor:
    def test_tags_are_removed(self, stream_no_color):
        info('<c:t1>t1</c> <c:t2,t3>t2,t3</c>')

        assert stream_no_color.getvalue() == 't1 t2,t3\n'

    def test_yuio_process_color_tags(self, stream_no_color):
        info('<c:t1>t1</c>', extra={'yuio_process_color_tags': False})

        assert stream_no_color.getvalue() == '<c:t1>t1</c>\n'

    def test_simple_logging(self, stream_no_color):
        debug('debug message')
        info('info message')
        warning('warning message')
        error('error message')

        assert (
            stream_no_color.getvalue() ==
            'debug message\n'
            'info message\n'
            'warning message\n'
            'error message\n'
        )


class TestLoggingColor:
    def test_yuio_process_color_tags(self, stream):
        info('<c:t1>t1</c>', extra={'yuio_process_color_tags': False})

        assert stream.getvalue() == '\033[0;39;49m<c:t1>t1</c>\n\033[0m'

    def test_simple_logging(self, stream):
        debug('debug message')
        info('info message')
        warning('warning message')
        error('error message')

        assert (
            stream.getvalue() ==
            '\033[0;39;49;2mdebug message\n\033[0m'
            '\033[0;39;49minfo message\n\033[0m'
            '\033[0;33;49mwarning message\n\033[0m'
            '\033[0;31;49merror message\n\033[0m'
        )

    def test_color_tags(self, stream):
        info('<c:red>red <c:bold>bold <c:green>green</c></c></c>')

        assert (
            stream.getvalue() ==
            '\033[0;39;49m'  # info log line color, color is normal
            '\033[0;31;49mred '  # opening red tag, color is red
            '\033[0;31;49;1mbold '  # opening bold tag, color is bold-red
            '\033[0;32;49;1mgreen'  # opening green tag, color is bold-green
            '\033[0;31;49;1m'  # closing green tag
            '\033[0;31;49m'  # closing bold tag
            '\033[0;39;49m\n'  # closing red tag
            '\033[0m'  # end of message, resetting all styles
        )

    def test_color_overrides(self):
        stream = io.StringIO()
        setup(
            use_colors=True, level=DEBUG, stream=stream, colors=dict(
                info=STYLE_BOLD,
                custom_tag=FORE_BLACK,
            )
        )

        info('<c:custom_tag>black</c>')

        assert (
            stream.getvalue() ==
            '\033[0;39;49;1m'  # info log line color, color is bold
            '\033[0;30;49;1mblack'  # opening custom tag, color is bold-black
            '\033[0;39;49;1m\n'  # closing custom tag
            '\033[0m'  # end of message, resetting all styles
        )


class TestTask:
    def test_no_color_logging(self, stream_no_color):
        task = Task('task description')

        # These are ignored in 'no color' mode.
        task.comment('comment')
        task.progress(0.5)

        info('info message')

        subtask = task.subtask('subtask description')

        subtask.done()

        task.done()

        assert (
            stream_no_color.getvalue() ==
            'task description...\n'
            'info message\n'
            'subtask description...\n'
            'subtask description: OK\n'
            'task description: OK\n'
        )

    def test_color_logging(self):
        stream = io.StringIO()

        setup(use_colors=True, level=DEBUG, stream=stream)

        task = Task('task description')

        task.comment('comment')
        task.progress(0.5)

        info('info message')

        task.done()

        assert (
            stream.getvalue() ==
            '\033[0;34;49mtask description...\033[0m\n'  # task start line
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask description - comment...\033[0m\n'  # add comment
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask description [------>        ] 50% - comment\033[0m\n'  # add progress
            '\033[1F\033[J'  # clear tasks
            '\033[0;39;49minfo message\n\033[0m'  # log info message
            '\033[0;34;49mtask description [------>        ] 50% - comment\033[0m\n'  # redraw task
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask description: OK\033[0m\n'  # task is OK
        )

    def test_task_context(self, stream):
        with Task('task 1'):
            pass

        try:
            with Task('task 2') as t2:
                t2.comment('comment')
                raise RuntimeError('scary error!!!')
        except RuntimeError as e:
            assert str(e) == 'scary error!!!'

        assert (
            stream.getvalue() ==
            '\033[0;34;49mtask 1...\033[0m\n'  # task start line
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask 1: OK\033[0m\n'  # task is OK
            '\033[0;34;49mtask 2...\033[0m\n'  # task start line
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask 2 - comment...\033[0m\n'  # add comment
            '\033[1F\033[J'  # clear tasks
            '\033[0;31;49mtask 2: ERROR\033[0m\n'  # task is OK
        )

    def test_subtask(self, stream):
        task = Task('task description')
        subtask = task.subtask('subtask description')
        sub_subtask = subtask.subtask('sub-subtask description')

        # note: don't mark sub_subtask as done
        subtask.done()
        task.error()

        assert (
            stream.getvalue() ==
            '\033[0;34;49mtask description...\033[0m\n'  # task start line
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask description...\033[0m\n'  # add subtask
            '\033[0;34;49m  subtask description...\033[0m\n'
            '\033[2F\033[J'  # clear tasks
            '\033[0;34;49mtask description...\033[0m\n'  # add sub-subtask
            '\033[0;34;49m  subtask description...\033[0m\n'
            '\033[0;34;49m    sub-subtask description...\033[0m\n'
            '\033[3F\033[J'  # clear tasks
            '\033[0;34;49mtask description...\033[0m\n'  # mark sub-subtask as done
            '\033[0;32;49m  subtask description: OK\033[0m\n'
            '\033[0;34;49m    sub-subtask description...\033[0m\n'
            '\033[3F\033[J'  # clear tasks
            '\033[0;31;49mtask description: ERROR\033[0m\n'  # task is ERROR
        )

    def test_progress(self, stream):
        task = Task('task')

        task.progress(0.3)
        task.progress((3, 15))
        task.progress((3, 5, 15))

        task.done()

        assert (
            stream.getvalue() ==
            '\033[0;34;49mtask...\033[0m\n'  # task start line
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask [--->           ] 30%\033[0m\n'  # progress 30%
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask [-->            ] 3 / 15\033[0m\n'  # progress 3 out of 15
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask [--->>>>>       ] 3 / 5 / 15\033[0m\n'  # progress 3 out of 15, 5 running
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask: OK\033[0m\n'  # task is OK
        )

    def test_iter(self, stream):
        with Task('task') as task:
            for _ in task.iter(range(3)):
                pass

        assert (
            stream.getvalue() ==
            '\033[0;34;49mtask...\033[0m\n'  # task start line
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask [               ] 0 / 3\033[0m\n'  # progress 0 out of 3
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask [---->          ] 1 / 3\033[0m\n'  # progress 1 out of 3
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask [--------->     ] 2 / 3\033[0m\n'  # progress 2 out of 3
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask [---------------] 3 / 3\033[0m\n'  # progress 3 out of 3
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask: OK\033[0m\n'  # task is OK
        )

    def test_iter_task_long(self, stream):
        with Task('task') as task:
            for _ in task.iter(range(1500)):
                pass

        log = stream.getvalue()

        assert log.startswith('\033[0;34;49mtask...\033[0m\n')
        assert log.count('\n') == 103
        assert log.count('\033[1F\033[J\033[0;34;49mtask') == 101
        assert log.endswith('\033[0;32;49mtask: OK\033[0m\n')

        for i in range(101):
            assert f' {i}%' in log

    def test_concurrent_tasks(self, stream):
        task1 = Task('task 1')
        task2 = Task('task 2')
        task2.done()
        task1.done()

        assert (
            stream.getvalue() ==
            '\033[0;34;49mtask 1...\033[0m\n'  # start task 1
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask 1...\033[0m\n'  # start task 1
            '\033[0;34;49mtask 2...\033[0m\n'
            '\033[2F\033[J'  # clear tasks
            '\033[0;32;49mtask 2: OK\033[0m\n'  # finish task 2
            '\033[0;34;49mtask 1...\033[0m\n'
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask 1: OK\033[0m\n'  # finish task 1
        )


class TestSuspend:
    def test_logging_is_suspended(self, stream):
        info('info message')

        with SuspendLogging():
            info('suspended message')
            log(1000, 'high priority message')

            assert stream.getvalue() == '\033[0;39;49minfo message\n\033[0m'

        assert (
            stream.getvalue() ==
            '\033[0;39;49minfo message\n\033[0m'
            '\033[0;39;49msuspended message\n\033[0m'
            '\033[0;39;49mhigh priority message\n\033[0m'
        )

    def test_logging_is_suspended_no_color(self, stream_no_color):
        info('info message')

        with SuspendLogging():
            info('suspended message')
            log(1000, 'high priority message')

            assert stream_no_color.getvalue() == 'info message\n'

        assert (
            stream_no_color.getvalue() ==
            'info message\n'
            'suspended message\n'
            'high priority message\n'
        )

    def test_tasks_are_suspended(self, stream):
        info('info message')

        with SuspendLogging():
            task = Task('task description')
            task.comment('comment')

            assert stream.getvalue() == '\033[0;39;49minfo message\n\033[0m'

        task.done()

        assert (
            stream.getvalue() ==
            '\033[0;39;49minfo message\n\033[0m'
            '\033[0;34;49mtask description - comment...\033[0m\n'
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask description: OK\033[0m\n'
        )

    def test_tasks_are_suspended_no_color(self, stream_no_color):
        info('info message')

        with SuspendLogging():
            task = Task('task description')
            task.comment('comment')
            task.subtask('task 2').done()

            info('info message 2')

            assert stream_no_color.getvalue() == 'info message\n'

        task.done()

        assert (
            stream_no_color.getvalue() ==
            'info message\n'
            'task description...\n'
            'task 2...\n'
            'task 2: OK\n'
            'info message 2\n'
            'task description: OK\n'
        )

    def test_suspended_override(self, stream):
        info('info message')

        with SuspendLogging() as logging:
            info('suspended message')

            logging.info('overridden message')
            logging.info('suspended message 2', extra={'yuio_ignore_suspended': False})
            info('overridden message 2', extra={'yuio_ignore_suspended': True})

            assert (
                stream.getvalue() ==
                '\033[0;39;49minfo message\n\033[0m'
                '\033[0;39;49moverridden message\n\033[0m'
                '\033[0;39;49moverridden message 2\n\033[0m'
            )

        assert (
            stream.getvalue() ==
            '\033[0;39;49minfo message\n\033[0m'
            '\033[0;39;49moverridden message\n\033[0m'
            '\033[0;39;49moverridden message 2\n\033[0m'
            '\033[0;39;49msuspended message\n\033[0m'
            '\033[0;39;49msuspended message 2\n\033[0m'
        )


class TestEdit:
    def test_noninteractive(self, stream_no_color):
        assert edit('String to edit') == 'String to edit'
        assert edit('# Comment\nString to edit') == 'String to edit'
        assert edit('  #Comment\nString to edit') == 'String to edit'

    def test_interactive(self, stream_interactive):
        assert edit('String to edit', editor='cat') == 'String to edit'
        assert edit('# Comment\nString to edit', editor='cat') == 'String to edit'
        assert edit('  #Comment\nString to edit', editor='cat') == 'String to edit'

    def test_replace(self, stream_interactive):
        assert edit('a\nx', editor='sed -i "" "s/a/b/g"') == 'b\nx'

    def test_detect_editor(self, stream_interactive, save_env):
        os.environ['EDITOR'] = 'sed -i "" "s/a/b/g"'

        assert edit('a\nx') == 'b\nx'

    def test_comment_marker(self):
        assert edit('// Comment\nString to edit', comment_marker='//') == 'String to edit'


class TestAsk:
    @pytest.fixture(autouse=True)
    def stdin_fixup(self, stream_interactive):
        stdin = sys.stdin
        yield
        sys.stdin = stdin

    out: AttyStream

    def prepare(self, input):
        self.out = AttyStream(True)
        setup(stream=self.out)
        sys.stdin = io.StringIO(input)

    def test_str(self):
        self.prepare('abc\n')
        assert ask('question') == 'abc'
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        self.prepare('\nabc\n')
        assert ask('question') == 'abc'
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
            '\033[0;31;49mInput is required.\n\033[0m'
            '\033[0;34;49mquestion: \033[0m'
        )

        self.prepare('\n')
        assert ask('question', default='abc') == 'abc'
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion [\033[0;32;49mabc\033[0;34;49m]: \033[0m'
        )

    def test_parser(self):
        self.prepare('10\n')
        assert ask('question', parser=yuio.parse.Int()) == 10
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        self.prepare('10\n11')
        assert ask('question', parser=yuio.parse.Int().gt(10)) == 11
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
            '\033[0;31;49mError: value should be greater than 10, got 10 instead.\n\033[0m'
            '\033[0;34;49mquestion: \033[0m'
        )

        self.prepare('True\n')
        assert ask('question', parser=yuio.parse.Bool()) is True
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        self.prepare('xxx\nno')
        assert ask('question', parser=yuio.parse.Bool()) is False
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
            '\033[0;31;49mError: could not parse value \'xxx\', enter either \'yes\' or \'no\'.\n\033[0m'
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        self.prepare('xxx\n\n')
        assert ask(
            'question',
            parser=yuio.parse.OneOf(
                yuio.parse.Str(),
                ['a', 'b']
            ),
            default='b'
        ) == 'b'
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (a|b) [\033[0;32;49mb\033[0;34;49m]: \033[0m'
            '\033[0;31;49mError: could not parse value \'xxx\', should be one of a, b.\n\033[0m'
            '\033[0;34;49mquestion (a|b) [\033[0;32;49mb\033[0;34;49m]: \033[0m'
        )

    def test_parser_from_type(self):
        self.prepare('10\n')
        assert ask('question', parser=int) == 10
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        self.prepare('True\n')
        assert ask('question', parser=bool) is True
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

    def test_descriptions(self):
        self.prepare('10\n')
        assert ask('question', parser=int, input_description='int') == 10
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (int): \033[0m'
        )

        self.prepare('True\n')
        assert ask('question', parser=bool, input_description='bool') is True
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (bool): \033[0m'
        )

        self.prepare('True\n')
        assert ask('question', parser=bool, input_description='') is True
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        self.prepare('\n')
        assert ask('question', parser=int, default=10) == 10
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion [\033[0;32;49m10\033[0;34;49m]: \033[0m'
        )

        self.prepare('\n')
        assert ask('question', parser=int, default=10, default_description='ten') == 10
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion [\033[0;32;49mten\033[0;34;49m]: \033[0m'
        )

        self.prepare('\n')
        assert ask('question', parser=int, default=10, default_description='') == 10
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

    def test_yn(self):
        self.prepare('True\n')
        assert ask_yn('question') is True
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        self.prepare('False\n')
        assert ask_yn('question') is False
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        self.prepare('\n')
        assert ask_yn('question', default=None) is None
        assert (
            self.out.getvalue() ==
            '\033[0;34;49mquestion (yes|no) [\033[0;32;49m<none>\033[0;34;49m]: \033[0m'
        )

    def test_wait(self):
        self.prepare('\n')
        wait_for_user()
        assert self.out.getvalue() == '\033[0;34;49mPress enter to continue\n\033[0m'

    def test_noninteractive(self, save_env):
        os.environ['TERM'] = 'dumb'

        assert ask('message', default='x') == 'x'
        assert ask('message', default=None) is None
        with pytest.raises(UserIoError):
            ask('message')
