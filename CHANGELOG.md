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

### Io

- ✨ Added `yuio.io.hl` and `yuio.io.out`.
- ✨ Added underline and italic font styles.
- 🔧 Changed `yuio.io.edit`'s `comment_marker` parameter now defaults to `None`
  to avoid confusion.
- 🐛 Fixed quoting when invoking editor command from `$VISUAL` or `$EDITOR`.

### App

- ✨ Added `--bug-report` flag.

### Config

- ✨ Added a check to defect config fields without type annotations.
- ✨ Added `yuio.config.Config.to_json_value`.
- 🔧 Field markers are now replaced with defaults upon config class creation, not
  lazily like it was before.

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

### Md

- 🐛 Fixed highlighting of escape sequences in strings.

### Term

- 💥 Split `yuio.term` into `yuio.term`, `yuio.color`, and `yuio.string`.

- ✨ Added check for Windows Terminal in WSL.

  Windows Terminal supports true colors, but doesn't set `COLORTERM` by default.
  We use `wslinfo` to detect this situation.

- 🔧 Changed detection of terminal capabilities in CI to respect terminal's
  `isatty` output. This will disable colored output in GitHub Actions because
  [GitHub uses pipes instead of TTY emulation]. However, this will prevent
  potential issues when Yuio programs running in CI are piped to somewhere else.

  To enable colors in GitHub, use `--force-colors` flag or set environment
  variable `FORCE_COLORS`.

- 🐛 Fixed a bug when pressing enter during Yuio initialization would cause
  remnants of OSC response to appear on screen.

- 🐛 Improved parsing of ANSI escape codes that come from terminals

## [2.0.0-rc0] - 2025-10-28

Release candidate for version 2.

[2.0.0-rc0]: https://github.com/taminomara/yuio/releases/tag/v2.0.0-rc0
[github uses pipes instead of tty emulation]: https://github.com/actions/runner/issues/241
[unreleased]: https://github.com/taminomara/yuio/compare/v2.0.0-rc0...HEAD
