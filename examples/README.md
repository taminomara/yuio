# Yuio examples

## App

- [app] — a CLI application with multiple subcommands.
- [custom_completer] — a application with custom CLI autocompletion.

## Io

- [io_colored_output.py] — pretty printing.
- [io_external_editor.py] — editing large text in external editor.
- [io_log_handling.py] — manual logging setup and colorized log printing.
- [io_prompt.py] — simple interactive prompts.
- [io_prompt_multiselect.py] — interactive prompts choose widgets based on type of input.
- [io_prompt_secret.py] — reading passwords from command line.
- [io_prompt_list.py] — reading list of integers and highlighting errors if an int can't be parsed.
- [io_tasks.py] — progress bars that handle printing and logging.
- [io_tasks_multithreaded.py] — displaying multiple progress bars, possible from different threads.
- [theme.py] — custom theme.

## Git

- [git.py] — query current repo status and log.

## Widgets

> **Note:** this demonstrates a low level API, see [io_prompt.py]
> for a higher level abstraction.

- [widgets/choice.py] — select one option of many.
- [widgets/multiselect.py] — select multiple options.
- [widgets/input.py] — simple input with a placeholder.
- [widgets/completion.py] — input with autocompletion.
- [widgets/completion_file.py] — input with autocompletion, with a file path completer.
- [widgets/vertical_layout.py] — stack widgets together.
- [widgets/help.py] — demonstration of built-in help menu.

## Docs

Examples used in [Yuio By Example] manual.

## Cook Book

Examples used in [Cook Book] manual.

[app]: ./app
[custom_completer]: ./custom_completer
[git.py]: ./git.py
[io_colored_output.py]: ./io_colored_output.py
[io_external_editor.py]: ./io_external_editor.py
[io_log_handling.py]: ./io_log_handling.py
[io_prompt_multiselect.py]: ./io_prompt_multiselect.py
[io_prompt_secret.py]: ./io_prompt_secret.py
[io_prompt_list.py]: ./io_prompt_list.py
[io_prompt.py]: ./io_prompt.py
[io_tasks_multithreaded.py]: ./io_tasks_multithreaded.py
[io_tasks.py]: ./io_tasks.py
[theme.py]: ./theme.py
[widgets/choice.py]: ./widgets/choice.py
[widgets/completion_file.py]: ./widgets/completion_file.py
[widgets/completion.py]: ./widgets/completion.py
[widgets/help.py]: ./widgets/help.py
[widgets/input.py]: ./widgets/input.py
[widgets/multiselect.py]: ./widgets/multiselect.py
[widgets/vertical_layout.py]: ./widgets/vertical_layout.py
[Yuio By Example]: https://yuio.readthedocs.io/en/stable/by_example/index.html
[Cook Book]: https://yuio.readthedocs.io/en/stable/cookbook/index.html
