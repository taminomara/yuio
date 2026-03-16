# Changelog

<!--
NOTE: if you're unsure which emojis to use, use the following prefixes instead of them
and run `poe lint` to replace:

- [added] ...
- [changed] ...
- [deprecated] ...
- [removed] ...
- [performance] ...
- [fixed] ...
-->

## [Unreleased]

- 🐛 Fixed issue with using `print` while in task.
- 🐛 Fixed detecting system stackframes on linux.

## [2.2.0] - 2026-03-11

- ✨ Added `yuio.ty.Pair`.

## [2.1.1] - 2026-02-17

- 🐛 Fixed help generation for positional-only app arguments.

## [2.1.0] - 2026-02-14

- ✨ Added `yuio.parse.Literal` and support for `typing.Literal`.

- ✨ `yuio.parse.Union` can use choice widget if all of its nested parsers can
  return options.

- ✨ Added `yuio.io.shell` to spawn an interactive shell with custom prompt
  prefix.

- ✨ Supported positional-only arguments in apps; these arguments create
  positional CLI options.

- ✨ Supported lazy loading of subcommands via `yuio.app.App.lazy_subcommand`.

- ✨ Added `yuio.string.Plural`, `yuio.string.Ordinal`.

- ✨ Added `limit` argument for `yuio.string.Join*`.

- ✨ Added `yuio.git.Status.get_ongoing_operation`.

- ⚠️ `yuio.config.positional` and passing `yuio.POSITIONAL` to
  `yuio.config.field` is pending deprecation, and will be deprecated unless
  someone reports a legitimate use-case for it.

- 🐛 Fixed file types in `yuio.ty`.

## [2.0.1] - 2026-01-31

- 🐛 Fixed rendering of Json Schema for dicts with string enum keys.

## [2.0.0] - 2026-01-31

- ✨ Stable release 🎉

## [2.0.0-rc5] - 2026-01-30

- ✨ Supported rendering hyperlinks in widgets.

## [2.0.0-rc4] - 2026-01-29

- ✨ Refactored `yuio.io.Task` to move its rendering logic to a widget, thus
  allowing tasks with custom widgets.

- ✨ Added `MessageChannel` abstraction.

- ✨ Added copy and deepcopy handlers for configs.

- ✨ Added documentation trimming when exporting JsonSchema for enums.

## [2.0.0-rc3] - 2026-01-26

- 💥 Add RST parser and make syntax for docstrings configurable; split `yuio.md`
  into `yuio.doc`, `yuio.md`, and `yuio.rst`.

- 💥 Updated Sphinx extension to add its own domain instead of relying on
  autodoc, added new cross-references and a directive to document commands.

- 💥 Renamed `yuio.GROUP` to `yuio.COLLAPSE`.

- 💥 Option groups no longer inspect config docstrings to infer help messages;
  now, config docstrings are not displayed outside of Sphinx.

- ✨ Added flag to collapse option groups when displaying CLI help message.

- ✨ CLI help now shows default flag values.

- ✨ Added magic attributes (`Enum.__yuio_by_name__`,
  `Enum.__yuio_to_dash_case__`, `Config.__yuio_short_help__`) that would help
  with parser specification and help generation.

- ✨ Added detection of on-going bisect to `Repo.status`.

- 🔧 `preserve_spaces=False` no longer collapses all consecutive spaces when
  wrapping a paragraph. Spaces are collapsed only when line break occurs.

- 🔧 Refactor code highlighters and move them into a separate module.

## [2.0.0-rc2] - 2026-01-04

- 🔧 Don't override all colors with their RGB values. This ensures that we
  respect user settings for using bright colors for bold text.

- 🔧 Export RGB colors in theme under `term/` path.

- 🐛 Don't display hidden subcommands in CLI help messages.

## [2.0.0-rc1] - 2026-01-03

Large refactoring around lower-level APIs, making them more flexible.

- 💥 Moved utility functions from top level to `yuio.util`.

- 💥 Renamed `App.command` to `App.wrapped` to avoid confusion between
  `App.command` and `App.subcommand`.

- 💥 Renamed `--force-color` to `--color`, allowed specifying exact level of
  color support via e.g. `--color=ansi-256`.

- 💥 Ditched `argparse` in favour of custom CLI parsing library `yuio.cli`.
  Behavior of CLI parser could've changed.

- 💥 Renamed and simplified parser methods.

- 💥 Removed `yuio.exec.sh`, it's really not going to be portable.

- 💥 Removed `skip_checks` parameter from constructor of `Repo`.

- 💥 Split `yuio.term` into `yuio.term`, `yuio.color`, and `yuio.string`; renamed
  a bunch of things.

- 💥 Split `Theme.msg_decorations` into `Theme.msg_decorations_unicode` and
  `Theme.msg_decorations_ascii`. One of them will be used depending on output
  stream encoding.

- ✨ Supported colorized multiline `str` and `repr`, supported Rich repr
  protocol.

- ✨ Added `yuio.PrettyException`.

- ✨ Added `yuio.io.hl`, `yuio.io.hr`.

- ✨ Added underline, italic, inverse and blink text styles.

- ✨ Supported colorized string interpolation in `%` formatting.

- ✨ Supported passing template strings to `yuio.io.info` and others.

- ✨ Added formatting utilities like `yuio.string.Format` and others.

- ✨ Added colorized log formatter (`yuio.io.Formatter`) that allows tweaking
  logs appearance.

- ✨ Improved recognition of color support, added additional setting for ASCII
  message decorations for terminals that don't use unicode.

- ✨ Added support for reading secret data without echoing it back to user.

- ✨ Added support for formatting hyperlinks (for terminals that support them).

- ✨ Added more control over CLI configuration, including a mechanism for
  overriding behavior of CLI options via subclassing `yuio.cli.Option`.

- ✨ Added `--bug-report` flag.

- ✨ Added `is_dev_mode` setting, exposed function to configure Yuio's internal
  logging.

- ✨ Added tracking of source location when parsing. Parsing errors now know
  where exactly an error has occurred.

- ✨ Added a check to detect config fields without type annotations.

- ✨ Added `yuio.config.Config.to_json_value`.

- ✨ Added `capture_io` and `logger` options to `yuio.io.exec`.

- ✨ Added `GitExecError`, `GitUnavailableError`, `GitUnavailableError`.

- ✨ Json schema for Enums now includes documentation for each member if it can
  be parsed.

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

- ✨ Added warnings for recursive color definitions in a theme.

- ✨ Added `Theme.check` that checks theme for consistency.

- 🔧 Changed `yuio.io.edit`'s `comment_marker` parameter now defaults to `None`
  to avoid confusion.

- 🔧 Field markers are now replaced with defaults upon config class creation, not
  lazily like it was before.

- 🔧 Improved error messages when loading configs from files and envs.

- 🔧 Allowed initializing `yuio.git.RefCompleter` without explicitly providing a
  `Repo` class.

- 🔧 Re-implemented `yuio.git.Repo.git` using `yuio.exec.exec`; renamed its
  `capture_output` parameter ro `capture_io`.

- 🔧 Switched from draft-2020 to draft-07 because VSCode still struggles with
  some of 2020's features.

- 🔧 Changed detection of terminal capabilities in CI to respect terminal's
  `isatty` output. This will disable colored output in GitHub Actions because
  [GitHub uses pipes instead of TTY emulation]. However, this will prevent
  potential issues when Yuio programs running in CI are piped to somewhere else.

  To enable colors in GitHub, use `--force-colors` flag or set environment
  variable `FORCE_COLOR`.

- 🔧 Improved `ColorizedString` to support no-wrap sequences and to avoid adding
  unnecessary color changes.

- 🔧 Documented available message decorations and color paths.

- ⚡ Moved message formatting outside of IO lock, now `yuio.io.raw` and
  `yuio.io.Format` handle all formatting and wrapping.

- ⚡ Implemented communication with subprocesses using `select` call on Unix
  operating systems.

- 🐛 Fixed quoting when invoking editor command from `$VISUAL` or `$EDITOR`.

- 🐛 Fixed highlighting of escape sequences in strings.

- 🐛 Fixed a bug when pressing enter during Yuio initialization would cause
  remnants of OSC response to appear on screen.

- 🐛 Improved parsing of ANSI escape codes that come from terminals.

- 🐛 Improved loading themes from files, bringing this functionality closer to
  being stable.

- 🐛 Fixed small bugs in fish and bash autocompletion scripts. Zsh is still a
  mess, though.

## [2.0.0-rc0] - 2025-10-28

Release candidate for version 2.

[2.0.0]: https://github.com/taminomara/yuio/compare/v2.0.0-rc5...v2.0.0
[2.0.0-rc0]: https://github.com/taminomara/yuio/releases/tag/v2.0.0-rc0
[2.0.0-rc1]: https://github.com/taminomara/yuio/compare/v2.0.0-rc0...v2.0.0-rc1
[2.0.0-rc2]: https://github.com/taminomara/yuio/compare/v2.0.0-rc1...v2.0.0-rc2
[2.0.0-rc3]: https://github.com/taminomara/yuio/compare/v2.0.0-rc2...v2.0.0-rc3
[2.0.0-rc4]: https://github.com/taminomara/yuio/compare/v2.0.0-rc3...v2.0.0-rc4
[2.0.0-rc5]: https://github.com/taminomara/yuio/compare/v2.0.0-rc4...v2.0.0-rc5
[2.0.1]: https://github.com/taminomara/yuio/compare/v2.0.0...v2.0.1
[2.1.0]: https://github.com/taminomara/yuio/compare/v2.0.1...v2.1.0
[2.1.1]: https://github.com/taminomara/yuio/compare/v2.1.0...v2.1.1
[2.2.0]: https://github.com/taminomara/yuio/compare/v2.1.1...v2.2.0
[github uses pipes instead of tty emulation]: https://github.com/actions/runner/issues/241
[unreleased]: https://github.com/taminomara/yuio/compare/v2.2.0...HEAD
