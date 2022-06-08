import io

from yuio.io import *


def test_color_output():
    assert str(Color()) == '\033[0m'
    assert str(Color(31)) == '\033[0;31m'
    assert str(Color(32, bold=True, dim=True)) == '\033[0;32;1;2m'
    assert str(Color(bold=True)) == '\033[0;1m'


def test_color_combine():
    assert Color(1) | Color(2) == Color(2)
    assert Color(1) | Color() == Color(1)
    assert Color() | Color(1) == Color(1)
    assert Color(1) | Color(bold=True) == Color(1, bold=True)
    assert Color(1, bold=True) | Color(2) == Color(2, bold=True)


def test_color_tags_are_removed_in_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    info('<c:t1>t1</c> <c:t2,t3>t2,t3</c>')

    assert stream.getvalue() == f't1 t2,t3\n'


def test_no_color_tags_property():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    info('<c:t1>t1</c>', extra={'no_color_tags': True})

    assert stream.getvalue() == f'<c:t1>t1</c>\n'


def test_simple_logging_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    debug('debug message')
    info('info message')
    warning('warning message')
    error('error message')

    assert stream.getvalue() == \
           f'debug message\n' \
           f'info message\n' \
           f'warning message\n' \
           f'error message\n'


def test_task_logging_ok_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    task_begin('task message')
    task_progress('task message', progress=0)
    task_progress('task message', progress=0.5)
    task_progress('task message', progress=1)
    task_done('task message')

    assert stream.getvalue() == \
           f'task message... OK\n'


def test_task_logging_err_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    task_begin('task message')
    task_progress('task message', progress=0)
    task_progress('task message', progress=0.5)
    task_progress('task message', progress=1)
    task_error('task message')

    assert stream.getvalue() == \
           f'task message... ERROR\n'


def test_multiline_task_logging_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    task_begin('task message line 1\ntask message line 2')
    task_progress('task message line 1\ntask message line 2', progress=0)
    task_progress('task message line 1\ntask message line 2', progress=1)
    task_done('task message line 1\ntask message line 2')

    assert stream.getvalue() == \
           f'task message line 1...\n' \
           f'task message line 2\n' \
           f'task message line 1... OK\n' \
           f'task message line 2\n'


def test_task_logging_interrupt_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    task_begin('task message')
    info('info message')
    task_done('task message')

    assert stream.getvalue() == \
           f'task message...\n' \
           f'info message\n' \
           f'task message... OK\n'


def test_task_logging_interrupt_with_other_task_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    task_begin('task 1 message')
    task_begin('task 2 message')
    task_done('task 1 message')
    task_done('task 2 message')

    assert stream.getvalue() == \
           f'task 1 message...\n' \
           f'task 2 message...\n' \
           f'task 1 message... OK\n' \
           f'task 2 message... OK\n'

    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    task_begin('task 1 message')
    task_begin('task 2 message')
    task_done('task 2 message')
    task_done('task 1 message')

    assert stream.getvalue() == \
           f'task 1 message...\n' \
           f'task 2 message... OK\n' \
           f'task 1 message... OK\n'


def test_task_logging_interrupt_with_question_no_colors():
    stream = io.StringIO()
    setup(use_colors=False, level=DEBUG, stream=stream)

    task_begin('task 1 message')
    question('prompt')

    assert stream.getvalue() == \
           f'task 1 message...\n' \
           f'prompt'


def test_simple_logging():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    debug('debug message')
    info('info message')
    warning('warning message')
    error('error message')

    assert stream.getvalue() == \
           f'\033[0;39;49;2mdebug message\n\033[0m' \
           f'\033[0;39;49minfo message\n\033[0m' \
           f'\033[0;33;49mwarning message\n\033[0m' \
           f'\033[0;31;49merror message\n\033[0m'


def test_color_tags():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    info('<c:red>red <c:bold>bold <c:green>green</c></c></c>')

    assert (
        stream.getvalue() ==
           f'\033[0;39;49m'  # info log line color, color is normal
           f'\033[0;31;49mred '  # opening red tag, color is red
           f'\033[0;31;49;1mbold '  # opening bold tag, color is bold-red
           f'\033[0;32;49;1mgreen'  # opening green tag, color is bold-green
           f'\033[0;31;49;1m'  # closing green tag
           f'\033[0;31;49m'  # closing bold tag
           f'\033[0;39;49m\n'  # closing red tag
           f'\033[0m'  # end of message, resetting all styles
    )


def test_color_overrides():
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
        f'\033[0;39;49;1m'  # info log line color, color is bold
        f'\033[0;30;49;1mblack'  # opening custom tag, color is bold-black
        f'\033[0;39;49;1m\n'  # closing custom tag
        f'\033[0m'  # end of message, resetting all styles
    )


def test_task_logging_ok():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    task_begin('task message')
    task_progress('task message', progress=0)
    task_progress('task message', progress=0.5)
    task_progress('task message', progress=1)
    task_done('task message')

    assert stream.getvalue() == \
           f'\033[0;34;49mtask message...\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [                    ] 0%\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [=========>          ] 50%\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [====================] 100%\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... OK\n\033[0m'


def test_task_logging_err():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    task_begin('task message')
    task_progress('task message', progress=0)
    task_progress('task message', progress=0.5)
    task_progress('task message', progress=1)
    task_error('task message')

    assert stream.getvalue() == \
           f'\033[0;34;49mtask message...\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [                    ] 0%\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [=========>          ] 50%\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [====================] 100%\033[0m' \
           f'\033[2K\r\033[0;31;49mtask message... ERROR\n\033[0m'


def test_task_logging_jobs():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    task_begin('task message')
    task_progress('task message', progress=(0, 10))
    task_progress('task message', progress=(5, 10))
    task_progress('task message', progress=(10, 10))
    task_done('task message')

    assert stream.getvalue() == \
           f'\033[0;34;49mtask message...\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [                    ] 0% (0 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [=========>          ] 50% (5 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [====================] 100% (10 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... OK\n\033[0m'


def test_task_logging_inflight_jobs():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    task_begin('task message')
    task_progress('task message', progress=(0, 0, 10))
    task_progress('task message', progress=(0, 2, 10))
    task_progress('task message', progress=(5, 0, 10))
    task_progress('task message', progress=(5, 5, 10))
    task_progress('task message', progress=(10, 0, 10))
    task_done('task message')

    assert stream.getvalue() == \
           f'\033[0;34;49mtask message...\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [                    ] 0% (0 / 0 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [>>>>                ] 0% (0 / 2 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [==========          ] 50% (5 / 0 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [==========>>>>>>>>>>] 50% (5 / 5 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [====================] 100% (10 / 0 / 10)\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... OK\n\033[0m'


def test_multiline_task_logging():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    task_begin('task message line 1\ntask message line 2')
    task_progress('task message line 1\ntask message line 2', progress=0.5)
    task_done('task message line 1\ntask message line 2')

    assert stream.getvalue() == \
           f'\033[0;34;49mtask message line 1...\n' \
           f'task message line 2\n\033[0m' \
           f'\033[0;34;49mtask message line 1... OK\n' \
           f'task message line 2\n\033[0m'


def test_task_interrupt():
    stream = io.StringIO()
    setup(use_colors=True, level=DEBUG, stream=stream)

    task_begin('task message')
    task_progress('task message', progress=0.5)
    info('info message')
    task_error('task message')

    assert stream.getvalue() == \
           f'\033[0;34;49mtask message...\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message... [=========>          ] 50%\033[0m' \
           f'\033[2K\r\033[0;34;49mtask message...\n\033[0m' \
           f'\033[0;39;49minfo message\n\033[0m' \
           f'\033[0;31;49mtask message... ERROR\n\033[0m'


def test_edit():
    os.environ['NON_INTERACTIVE'] = '1'

    text = edit(
        '# Comment\n'
        'Text'
    )

    assert text == 'Text'
