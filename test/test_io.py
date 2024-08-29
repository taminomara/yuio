# import io

# import pytest

# import yuio.io
# import yuio.parse
# import yuio.term


# class AttyStream(io.StringIO):
#     def __init__(self, atty: bool):
#         super().__init__()
#         self.atty = atty

#     def isatty(self):
#         return self.atty


# @pytest.fixture(autouse=True)
# def reset_logging():
#     yuio.io._MSG_HANDLER_IMPL.stream = AttyStream(False)
#     yuio.io._MSG_HANDLER_IMPL.use_colors = False
#     yuio.io._MSG_HANDLER_IMPL.colors = yuio.io.DEFAULT_COLORS
#     yuio.io._MSG_HANDLER_IMPL._tasks = []
#     yuio.io._MSG_HANDLER_IMPL._tasks_shown = 0
#     yuio.io._MSG_HANDLER_IMPL._suspended = 0
#     yuio.io._MSG_HANDLER_IMPL._suspended_lines = []

#     yield

#     assert yuio.io._MSG_HANDLER_IMPL._tasks == []
#     assert yuio.io._MSG_HANDLER_IMPL._tasks_shown == 0
#     assert yuio.io._MSG_HANDLER_IMPL._suspended == 0
#     assert yuio.io._MSG_HANDLER_IMPL._suspended_lines == []
