# Changelog

<!--
NOTE: if you're unsure which emojis to use, use the following prefixes instead of them
and run `pre-commit run clk` to replace:

- [added] ...
- [changed] ...
- [deprecated] ...
- [removed] ...
- [performance] ...
- [fixed] ...
-->

## [Unreleased]

Large refactoring around lower-level APIs, making them more flexible.

### Io

- ✨ Added `yuio.io.hl`, `yuio.io.hr`.
- ✨ Added underline, italic, inverse and blink text styles.
- ✨ Supported colorized multiline repr.
- ✨ Supported colorized string interpolation in `%` formatting.
- ✨ Added formatting utilities like `yuio.string.Format` and others.
- ✨ Added colorized log formatter (`yuio.io.Formatter`) that allows tweaking
  logs appearance.
- 🔧 Changed `yuio.io.edit`'s `comment_marker` parameter now defaults to `None`
  to avoid confusion.
- ⚡ Moved message formatting outside of IO lock, now `yuio.io.raw` and
  `yuio.io.Format` handle all formatting and wrapping.
- 🐛 Fixed quoting when invoking editor command from `$VISUAL` or `$EDITOR`.

### App

- 💥 Renamed `App.command` to `App.wrapped` to avoid confusion between
  `App.command` and `App.subcommand`.
- ✨ Added `--bug-report` flag.
- ✨ Added `is_dev_mode` setting, exposed function to configure Yuio's internal
  logging.

### Config

- ✨ Added a check to defect config fields without type annotations.
- ✨ Added `yuio.config.Config.to_json_value`.
- 🔧 Field markers are now replaced with defaults upon config class creation, not
  lazily like it was before.
- 🔧 Improved error messages when loading configs from files.

### Exec

- 💥 Removed `yuio.exec.sh`, it's really not going to be portable.
- ✨ Added `capture_io` and `logger` options to `yuio.io.exec`.
- ⚡ Implemented communication with subprocesses using `select` call on unix
  operating systems.

### Git

- 💥 Removed `skip_checks` parameter from constructor of `yuio.git.Repo`.
- ✨ Added `GitExecError`, `GitUnavailableError`, `GitUnavailableError`.
- 🔧 Allowed initializing `yuio.git.RefCompleter` without explicitly providing a
  `Repo` class.
- 🔧 Re-implemented `yuio.git.Repo.git` using `yuio.exec.exec`; renamed its
  `capture_output` parameter ro `capture_io`.

### Json Schema

- ✨ Json schema for Enums now includes documentation for each member if it can
  be parsed.
- 🔧 Switched from draft-2020 to draft-07 because VSCode still struggles with
  some of 2020's features.

### Term

- 💥 Split `yuio.term` into `yuio.term`, `yuio.color`, and `yuio.string`.

- 💥 Renamed `Term.terminal_colors` to `Term.terminal_theme`. Rename also affects
  keyword arguments of `get_term_from_stream`

- ✨ Markdown formatter and code highlighters will remove common indentation from
  source markdown by default. This can be disabled by setting flag
  `dedent=False`.

- ✨ Added check for Windows Terminal in WSL.

  Windows Terminal supports true colors, but doesn't set `COLORTERM` by default.
  We use `wslinfo` to detect this situation.

- ✨ Added `kwargs` to `Color.fore_from_*` and `Color.back_from_*`, allowing
  users to set text styles with these functions.

- ✨ Supported trimming long lines while wrapping text and replacing their tails
  with ellipsis.

- ✨ Added `Term.is_unicode` flag.

- 🔧 Changed detection of terminal capabilities in CI to respect terminal's
  `isatty` output. This will disable colored output in GitHub Actions because
  [GitHub uses pipes instead of TTY emulation]. However, this will prevent
  potential issues when Yuio programs running in CI are piped to somewhere else.

  To enable colors in GitHub, use `--force-colors` flag or set environment
  variable `FORCE_COLOR`.

- 🔧 Improved `ColorizedString` to support no-wrap sequences and to avoid adding
  unnecessary color changes.

- 🐛 Fixed highlighting of escape sequences in strings.

- 🐛 Fixed a bug when pressing enter during Yuio initialization would cause
  remnants of OSC response to appear on screen.

- 🐛 Improved parsing of ANSI escape codes that come from terminals.

### Theme

- ✨ Added warnings for recursive color definitions in a theme.
- ✨ Added `Theme.check` that checks theme for consistency.
- 🔧 Documented available message decorations and color paths.
- 🐛 Improved loading themes from files, bringing this functionality closer to
  being stable.

## [2.0.0-rc0] - 2025-10-28

Release candidate for version 2.

[2.0.0-rc0]: https://github.com/taminomara/yuio/releases/tag/v2.0.0-rc0
[github uses pipes instead of tty emulation]: https://github.com/actions/runner/issues/241
[unreleased]: https://github.com/taminomara/yuio/compare/v2.0.0-rc0...HEAD
