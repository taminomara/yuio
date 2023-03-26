import io
import sys

import pytest

import yuio.io
import yuio.parse


class AttyStream(io.StringIO):
    def __init__(self, atty: bool):
        super().__init__()
        self.atty = atty

    def isatty(self):
        return self.atty


@pytest.fixture(autouse=True)
def reset_logging():
    yuio.io._MSG_HANDLER_IMPL.stream = AttyStream(False)
    yuio.io._MSG_HANDLER_IMPL.use_colors = False
    yuio.io._MSG_HANDLER_IMPL.colors = yuio.io.DEFAULT_COLORS
    yuio.io._MSG_HANDLER_IMPL._tasks = []
    yuio.io._MSG_HANDLER_IMPL._tasks_shown = 0
    yuio.io._MSG_HANDLER_IMPL._suspended = 0
    yuio.io._MSG_HANDLER_IMPL._suspended_lines = []

    yield

    assert yuio.io._MSG_HANDLER_IMPL._tasks == []
    assert yuio.io._MSG_HANDLER_IMPL._tasks_shown == 0
    assert yuio.io._MSG_HANDLER_IMPL._suspended == 0
    assert yuio.io._MSG_HANDLER_IMPL._suspended_lines == []


@pytest.fixture
def stream(reset_logging):
    stream = AttyStream(False)
    yuio.io.setup(use_colors=True, level=yuio.io.LogLevel.DEBUG, stream=stream)

    yield stream

    yuio.io.setup()


@pytest.fixture
def stream_no_color(reset_logging):
    stream = AttyStream(False)
    yuio.io.setup(use_colors=False, level=yuio.io.LogLevel.DEBUG, stream=stream)

    yield stream

    yuio.io.setup()


@pytest.fixture
def stream_interactive(save_env, reset_logging):
    yuio.io.os.environ['TERM'] = 'xterm-256color'

    stream = AttyStream(True)
    yuio.io.setup(use_colors=True, level=yuio.io.LogLevel.DEBUG, stream=stream)

    yield stream

    yuio.io.setup()


class TestColor:
    def test_output(self):
        assert str(yuio.io.Color()) == '\033[0m'
        assert str(yuio.io.Color(31)) == '\033[0;31m'
        assert str(yuio.io.Color(32, bold=True, dim=True)) == '\033[0;32;1;2m'
        assert str(yuio.io.Color(bold=True)) == '\033[0;1m'

    def test_combine(self):
        assert yuio.io.Color(1) | yuio.io.Color(2) == yuio.io.Color(2)
        assert yuio.io.Color(1) | yuio.io.Color() == yuio.io.Color(1)
        assert yuio.io.Color() | yuio.io.Color(1) == yuio.io.Color(1)
        assert yuio.io.Color(1) | yuio.io.Color(bold=True) == yuio.io.Color(1, bold=True)
        assert yuio.io.Color(1, bold=True) | yuio.io.Color(2) == yuio.io.Color(2, bold=True)


class TestHelpers:
    def test_detect_editor(self, save_env):
        yuio.io.os.environ['EDITOR'] = 'subl -nw'

        assert yuio.io.detect_editor() == 'subl -nw'

    def test_is_interactive(self, save_env):
        yuio.io.os.environ['TERM'] = 'xterm-256color'

        yuio.io.setup(stream=AttyStream(True))
        assert yuio.io.is_interactive()

        yuio.io.setup(stream=AttyStream(False))
        assert not yuio.io.is_interactive()

        yuio.io.os.environ['TERM'] = 'dumb'
        yuio.io.setup(stream=AttyStream(True))
        assert not yuio.io.is_interactive()


class TestSetup:
    def test_level(self, stream_no_color):
        yuio.io.setup(level=yuio.io.LogLevel.WARNING)
        yuio.io.debug('debug message 1')
        yuio.io.info('info message 1')
        yuio.io.warning('warning message 1')

        yuio.io.setup(level=yuio.io.LogLevel.INFO)
        yuio.io.debug('debug message 2')
        yuio.io.info('info message 2')
        yuio.io.warning('warning message 2')

        assert (
            stream_no_color.getvalue() ==
            'warning message 1\n'
            'info message 2\n'
            'warning message 2\n'
        )

    def test_formatter(self, stream_no_color):
        yuio.io.setup(formatter=yuio.io.logging.Formatter('-> %(message)s'))
        yuio.io.info('info message 1')
        yuio.io.setup()
        yuio.io.info('info message 2')
        yuio.io.setup(formatter=yuio.io.logging.Formatter('%(message)s'))
        yuio.io.info('info message 3')

        assert (
            stream_no_color.getvalue() ==
            '-> info message 1\n'
            '-> info message 2\n'
            'info message 3\n'
        )

    def test_level_question(self, stream_no_color):
        yuio.io.setup(level=yuio.io.LogLevel.CRITICAL)
        yuio.io.error('error message 1')
        yuio.io.question('question message 1 ')
        yuio.io.setup(level=yuio.io.LogLevel.QUESTION)
        yuio.io.error('error message 2')
        yuio.io.question('question message 2 ')  # logged bc questions can't be disabled

        assert (
            stream_no_color.getvalue() ==  # questions don't produce newlines
            'question message 1 question message 2 '
        )

    def test_custom_tags(self, stream):
        yuio.io.setup(colors={'my_tag': yuio.io.Color.FORE_RED})
        yuio.io.info('using <c:my_tag>tag</c>')

        assert (
            stream.getvalue() ==
            '\033[0;39;49musing \033[0;31;49mtag\033[0;39;49m\033[0m\n'
        )

        with pytest.raises(RuntimeError, match='invalid tag \'my-tag\''):
            yuio.io.setup(colors={'my-tag': yuio.io.Color.FORE_RED})

        with pytest.raises(RuntimeError, match='invalid tag \'MY_TAG\''):
            yuio.io.setup(colors={'MY_TAG': yuio.io.Color.FORE_RED})


class TestLoggingNoColor:
    def test_tags_are_removed(self, stream_no_color):
        yuio.io.info('<c:t1>t1</c> <c:t2,t3>t2,t3</c>')

        assert stream_no_color.getvalue() == 't1 t2,t3\n'

    def test_yuio_process_color_tags(self, stream_no_color):
        yuio.io.info('<c:t1>t1</c>', extra={'yuio_process_color_tags': False})

        assert stream_no_color.getvalue() == '<c:t1>t1</c>\n'

    def test_simple_logging(self, stream_no_color):
        yuio.io.debug('debug message')
        yuio.io.info('info message')
        yuio.io.warning('warning message')
        yuio.io.error('error message')
        yuio.io.question('question message')

        assert (
            stream_no_color.getvalue() ==
            'debug message\n'
            'info message\n'
            'warning message\n'
            'error message\n'
            'question message'
        )


class TestLoggingColor:
    def test_yuio_process_color_tags(self, stream):
        yuio.io.info('<c:t1>t1</c>', extra={'yuio_process_color_tags': False})

        assert stream.getvalue() == '\033[0;39;49m<c:t1>t1</c>\033[0m\n'

    def test_simple_logging(self, stream):
        yuio.io.debug('debug message')
        yuio.io.info('info message')
        yuio.io.warning('warning message')
        yuio.io.error('error message')
        yuio.io.question('question message')

        assert (
            stream.getvalue() ==
            '\033[0;39;49;2mdebug message\033[0m\n'
            '\033[0;39;49minfo message\033[0m\n'
            '\033[0;33;49mwarning message\033[0m\n'
            '\033[0;31;49merror message\033[0m\n'
            '\033[0;34;49mquestion message\033[0m'
        )

    def test_color_tags(self, stream):
        yuio.io.info('<c:red>red <c:bold>bold <c:green>green</c></c></c>')

        assert (
            stream.getvalue() ==
            '\033[0;39;49m'  # info log line color, color is normal
            '\033[0;31;49mred '  # opening red tag, color is red
            '\033[0;31;49;1mbold '  # opening bold tag, color is bold-red
            '\033[0;32;49;1mgreen'  # opening green tag, color is bold-green
            '\033[0;31;49;1m'  # closing green tag
            '\033[0;31;49m'  # closing bold tag
            '\033[0;39;49m'  # closing red tag
            '\033[0m\n'  # end of message, resetting all styles
        )

    def test_color_overrides(self, stream):
        yuio.io.setup(
            use_colors=True, level=yuio.io.LogLevel.DEBUG, colors=dict(
                info=yuio.io.Color.STYLE_BOLD,
                custom_tag=yuio.io.Color.FORE_BLACK,
            )
        )

        yuio.io.info('<c:custom_tag>black</c>')

        assert (
            stream.getvalue() ==
            '\033[0;39;49;1m'  # info log line color, color is bold
            '\033[0;30;49;1mblack'  # opening custom tag, color is bold-black
            '\033[0;39;49;1m'  # closing custom tag
            '\033[0m\n'  # end of message, resetting all styles
        )

    def test_color_tags_in_exception(self, stream):
        import traceback

        try:
            # Color tags in exception messages and tracebacks are not processed.
            raise RuntimeError('<c:green>exception</c>')
        except RuntimeError as e:
            yuio.io.exception('oh no!')

            frame = traceback.extract_tb(e.__traceback__)[0]
            fname = frame.filename
            fline = frame.lineno

        assert (
            stream.getvalue() ==
            f'\033[0;31;49moh no!\n'
            f'Traceback (most recent call last):\n'
            f'\033[0;31;49m  File \033[0;32;49m"{fname}"\033[0;31;49m, line \033[0;32;49m{fline}\033[0;31;49m, in \033[0;32;49mtest_color_tags_in_exception\033[0;31;49m\n'
            f'  \033[0;31;49;1m  raise RuntimeError(\'<c:green>exception</c>\')\n'
            f'\033[0;31;49m\033[0;31;49mRuntimeError: <c:green>exception</c>\033[0m\n'
        )


class TestTask:
    def test_no_color_logging(self, stream_no_color):
        task = yuio.io.Task('task description')

        # These are ignored in 'no color' mode.
        task.comment('comment')
        task.progress(0.5)

        yuio.io.info('info message')

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

    def test_color_logging(self, stream):
        task = yuio.io.Task('task description')

        task.comment('comment')
        task.progress(0.5)

        yuio.io.info('info message')

        task.done()

        assert (
            stream.getvalue() ==
            '\033[0;34;49mtask description...\033[0m\n'  # task start line
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask description - comment...\033[0m\n'  # add comment
            '\033[1F\033[J'  # clear tasks
            '\033[0;34;49mtask description [------>        ] 50% - comment\033[0m\n'  # add progress
            '\033[1F\033[J'  # clear tasks
            '\033[0;39;49minfo message\033[0m\n'  # log info message
            '\033[0;34;49mtask description [------>        ] 50% - comment\033[0m\n'  # redraw task
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask description: OK\033[0m\n'  # task is OK
        )

    def test_task_context(self, stream):
        with yuio.io.Task('task 1'):
            pass

        try:
            with yuio.io.Task('task 2') as t2:
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
        task = yuio.io.Task('task description')
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
        task = yuio.io.Task('task')

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
        with yuio.io.Task('task') as task:
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
        with yuio.io.Task('task') as task:
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
        task1 = yuio.io.Task('task 1')
        task2 = yuio.io.Task('task 2')
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
        yuio.io.info('info message')

        with yuio.io.SuspendLogging():
            yuio.io.info('suspended message')
            yuio.io.log(yuio.io.LogLevel(1000), 'high priority message')

            assert stream.getvalue() == '\033[0;39;49minfo message\033[0m\n'

        assert (
            stream.getvalue() ==
            '\033[0;39;49minfo message\033[0m\n'
            '\033[0;39;49msuspended message\033[0m\n'
            '\033[0;39;49mhigh priority message\033[0m\n'
        )

    def test_logging_is_suspended_no_color(self, stream_no_color):
        yuio.io.info('info message')

        with yuio.io.SuspendLogging():
            yuio.io.info('suspended message')
            yuio.io.log(yuio.io.LogLevel(1000), 'high priority message')

            assert stream_no_color.getvalue() == 'info message\n'

        assert (
            stream_no_color.getvalue() ==
            'info message\n'
            'suspended message\n'
            'high priority message\n'
        )

    def test_tasks_are_suspended(self, stream):
        yuio.io.info('info message')

        with yuio.io.SuspendLogging():
            task = yuio.io.Task('task description')
            task.comment('comment')

            assert stream.getvalue() == '\033[0;39;49minfo message\033[0m\n'

        task.done()

        assert (
            stream.getvalue() ==
            '\033[0;39;49minfo message\033[0m\n'
            '\033[0;34;49mtask description - comment...\033[0m\n'
            '\033[1F\033[J'  # clear tasks
            '\033[0;32;49mtask description: OK\033[0m\n'
        )

    def test_tasks_are_suspended_no_color(self, stream_no_color):
        yuio.io.info('info message')

        with yuio.io.SuspendLogging():
            task = yuio.io.Task('task description')
            task.comment('comment')
            task.subtask('task 2').done()

            yuio.io.info('info message 2')

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
        yuio.io.info('info message')

        with yuio.io.SuspendLogging() as logging:
            yuio.io.info('suspended message')

            logging.info('overridden message')
            logging.info('suspended message 2', extra={'yuio_ignore_suspended': False})
            yuio.io.info('overridden message 2', extra={'yuio_ignore_suspended': True})

            assert (
                stream.getvalue() ==
                '\033[0;39;49minfo message\033[0m\n'
                '\033[0;39;49moverridden message\033[0m\n'
                '\033[0;39;49moverridden message 2\033[0m\n'
            )

        assert (
            stream.getvalue() ==
            '\033[0;39;49minfo message\033[0m\n'
            '\033[0;39;49moverridden message\033[0m\n'
            '\033[0;39;49moverridden message 2\033[0m\n'
            '\033[0;39;49msuspended message\033[0m\n'
            '\033[0;39;49msuspended message 2\033[0m\n'
        )


class TestEdit:
    def test_noninteractive(self):
        assert yuio.io.edit('String to edit') == 'String to edit'
        assert yuio.io.edit('# Comment\nString to edit') == 'String to edit'
        assert yuio.io.edit('  #Comment\nString to edit') == 'String to edit'

    def test_interactive(self, stream_interactive):
        assert yuio.io.edit('String to edit', editor='cat') == 'String to edit'
        assert yuio.io.edit('# Comment\nString to edit', editor='cat') == 'String to edit'
        assert yuio.io.edit('  #Comment\nString to edit', editor='cat') == 'String to edit'

    def test_replace(self, stream_interactive):
        assert yuio.io.edit('a\nx', editor='sed -i "" "s/a/b/g"') == 'b\nx'

    def test_detect_editor(self, stream_interactive, save_env):
        yuio.io.os.environ['EDITOR'] = 'sed -i "" "s/a/b/g"'

        assert yuio.io.edit('a\nx') == 'b\nx'

    def test_comment_marker(self):
        assert (
            yuio.io.edit(
                '// Comment\n'
                'String to edit 1\n'
                '// Comment\n'
                'String to edit 2\n'
                '// Comment',
                comment_marker='//'
            ) == (
                'String to edit 1\n'
                'String to edit 2'
            )
        )


class TestAsk:
    @pytest.fixture(autouse=True)
    def auto_fixtures(self, stream_interactive, save_stdin):
        pass

    @staticmethod
    def prepare(input):
        output = AttyStream(True)
        yuio.io.setup(stream=output, use_colors=True)
        yuio.io.sys.stdin = io.StringIO(input)
        return output

    def test_str(self):
        output = self.prepare('abc\n')
        assert yuio.io.ask('question') == 'abc'
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        output = self.prepare('\nabc\n')
        assert yuio.io.ask('question') == 'abc'
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
            '\033[0;31;49mInput is required.\033[0m\n'
            '\033[0;34;49mquestion: \033[0m'
        )

        output = self.prepare('\n')
        assert yuio.io.ask('question', default='abc') == 'abc'
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion [\033[0;32;49mabc\033[0;34;49m]: \033[0m'
        )

    def test_parser(self):
        output = self.prepare('10\n')
        assert yuio.io.ask('question', parser=yuio.io.yuio.parse.Int()) == 10
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        output = self.prepare('10\n11')
        assert yuio.io.ask('question', parser=yuio.io.yuio.parse.Int().gt(10)) == 11
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
            '\033[0;31;49mError: value should be greater than 10, got 10 instead.\033[0m\n'
            '\033[0;34;49mquestion: \033[0m'
        )

        output = self.prepare('True\n')
        assert yuio.io.ask('question', parser=yuio.io.yuio.parse.Bool()) is True
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        output = self.prepare('xxx\nno')
        assert yuio.io.ask('question', parser=yuio.io.yuio.parse.Bool()) is False
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
            '\033[0;31;49mError: could not parse value \'xxx\', enter either \'yes\' or \'no\'.\033[0m\n'
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        output = self.prepare('xxx\n\n')
        assert yuio.io.ask(
            'question',
            parser=yuio.io.yuio.parse.OneOf(
                yuio.io.yuio.parse.Str(),
                ['a', 'b']
            ),
            default='b'
        ) == 'b'
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (a|b) [\033[0;32;49mb\033[0;34;49m]: \033[0m'
            '\033[0;31;49mError: could not parse value \'xxx\', should be one of a, b.\033[0m\n'
            '\033[0;34;49mquestion (a|b) [\033[0;32;49mb\033[0;34;49m]: \033[0m'
        )

    def test_parser_from_type(self):
        output = self.prepare('10\n')
        assert yuio.io.ask('question', parser=int) == 10
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        output = self.prepare('True\n')
        assert yuio.io.ask('question', parser=bool) is True
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

    def test_descriptions(self):
        output = self.prepare('10\n')
        assert yuio.io.ask('question', parser=int, input_description='int') == 10
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (int): \033[0m'
        )

        output = self.prepare('True\n')
        assert yuio.io.ask('question', parser=bool, input_description='bool') is True
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (bool): \033[0m'
        )

        output = self.prepare('True\n')
        assert yuio.io.ask('question', parser=bool, input_description='') is True
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

        output = self.prepare('\n')
        assert yuio.io.ask('question', parser=int, default=10) == 10
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion [\033[0;32;49m10\033[0;34;49m]: \033[0m'
        )

        output = self.prepare('\n')
        assert yuio.io.ask('question', parser=int, default=10, default_description='ten') == 10
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion [\033[0;32;49mten\033[0;34;49m]: \033[0m'
        )

        output = self.prepare('\n')
        assert yuio.io.ask('question', parser=int, default=10, default_description='') == 10
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion: \033[0m'
        )

    def test_yn(self):
        output = self.prepare('True\n')
        assert yuio.io.ask_yn('question') is True
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        output = self.prepare('False\n')
        assert yuio.io.ask_yn('question') is False
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (yes|no): \033[0m'
        )

        output = self.prepare('\n')
        assert yuio.io.ask_yn('question', default=None) is None
        assert (
            output.getvalue() ==
            '\033[0;34;49mquestion (yes|no) [\033[0;32;49m<none>\033[0;34;49m]: \033[0m'
        )

    def test_wait(self):
        output = self.prepare('\n')
        yuio.io.wait_for_user()
        assert output.getvalue() == '\033[0;34;49mPress \033[0;32;49menter\033[0;34;49m to continue\n\033[0m'

    def test_noninteractive(self, save_env):
        yuio.io.os.environ['TERM'] = 'dumb'

        assert yuio.io.ask('message', default='x') == 'x'
        assert yuio.io.ask('message', default=None) is None
        with pytest.raises(yuio.io.UserIoError):
            yuio.io.ask('message')
