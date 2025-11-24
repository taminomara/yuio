# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides functionality for collecting data about environment for including
it to bug reports.

.. autofunction:: print_report

.. autoclass:: ReportSettings
    :members:

.. autoclass:: Report
    :members:

.. type:: EnvCollector
    :canonical: typing.Callable[[], Report] | Report

    Type alias for report collector.

"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime
import os
import re
import sys
import textwrap
import threading
import traceback
import types
from dataclasses import dataclass

from yuio import _typing as _t

if _t.TYPE_CHECKING:
    import yuio.app


@dataclass
class Report:
    """
    An environment report.

    """

    title: str
    """
    Report title.

    """

    items: list[str | tuple[str, str]] = dataclasses.field(default_factory=list)
    """
    Report items. Each item can be a string or a key-value pair of strings.

    """

    def __str__(self) -> str:
        return self.__class__.__name__


EnvCollector: _t.TypeAlias = _t.Callable[[], Report]
"""
A callable that collects a report.

"""

_LOCK = threading.Lock()
_ENV_COLLECTORS: list[tuple[str, EnvCollector | Report]] | None = None


@dataclass
class ReportSettings:
    """
    Settings for collecting debug data.

    """

    package: str | types.ModuleType | None = None
    """
    Root package. Used to collect dependencies.

    """

    dependencies: list[str | types.ModuleType] | None = None
    """
    List of additional dependencies to include to version report.

    """

    collectors: list[tuple[str, EnvCollector | Report]] | None = None
    """
    List of additional env collectors to run.

    """


def _get_env_collectors():
    global _ENV_COLLECTORS
    if _ENV_COLLECTORS is None:
        with _LOCK:
            if _ENV_COLLECTORS is None:
                _ENV_COLLECTORS = _load_env_collectors()
    return _ENV_COLLECTORS


def _load_env_collectors():
    import importlib.metadata

    collectors: list[tuple[str, EnvCollector | Report]] = []

    for plugin in importlib.metadata.entry_points(group="yuio.env_collector"):
        try:
            collectors.append((plugin.name, plugin.load()))
        except Exception:
            msg = "Error when loading cnv collector:\n" + traceback.format_exc()
            collectors.append((plugin.name, Report(plugin.name, [msg])))

    return collectors


@contextlib.contextmanager
def report_exc(report: Report, key: str | None):
    try:
        yield
    except Exception as e:
        msg = f"Can't collect this data: {e}"
        if key is not None:
            report.items.append((key, msg))
        else:
            report.items.append(msg)


def _system() -> Report:
    import platform

    report = Report("System", [])

    now = datetime.datetime.now(datetime.timezone.utc)
    report.items.append(("date", now.strftime("%Y-%m-%d %H:%M:%S")))
    with report_exc(report, "platform"):
        report.items.append(("platform", f"{sys.platform} ({platform.platform()})"))
    with report_exc(report, "os"):
        os = platform.system()
        if os == "Linux":
            data = platform.freedesktop_os_release()
            report.items.append(("os", f"{data['NAME']} {data['VERSION_ID']}"))
        elif os == "Windows":
            report.items.append(("os", " ".join(platform.win32_ver())))
        elif os == "Darwin":
            report.items.append(("os", platform.mac_ver()[0]))
        else:
            report.items.append(("os", os))
    with report_exc(report, "python"):
        report.items.append(
            ("python", f"{platform.python_implementation()} {sys.version}")
        )
    with report_exc(report, "machine"):
        report.items.append(
            ("machine", f"{platform.machine()} {platform.architecture()[0]}")
        )
    return report


def _versions(
    settings: ReportSettings, app: yuio.app.App[_t.Any] | None = None
) -> Report:
    report = Report("Versions")

    package = settings.package
    if app and app.version:
        report.items.append(("app", str(app.version)))
    if app and package is None:
        package = app._command.__module__

    packages = _get_requires(package)
    for package in settings.dependencies or []:
        if not isinstance(package, (str, types.ModuleType)):
            raise TypeError(
                f"expected str or ModuleType, got {_t.type_repr(type(package))}: {package!r}"
            )
        if isinstance(package, types.ModuleType):
            package = package.__name__
        packages.add(package)
    packages.add("yuio")

    for package in packages:
        with report_exc(report, package):
            report.items.append((package, _find_package_version(package)))

    return report


def _get_requires(package: str | types.ModuleType | None) -> set[str]:
    import importlib.metadata

    if package is None:
        return set()

    if not isinstance(package, (str, types.ModuleType)):
        raise TypeError(
            f"expected str or ModuleType, got {_t.type_repr(type(package))}: {package!r}"
        )

    if isinstance(package, types.ModuleType):
        package = package.__name__
    if "." in package:
        package = package.split(".")[0]
    if package == "__main__":
        return set()

    distribution = importlib.metadata.distribution(package)
    requires = distribution.requires
    packages = {package}
    if not requires:
        return packages
    for requirement in requires:
        if match := re.match(r"^\s*([\w-]+)\s*(\[[\w,\s-]*\])?", requirement):
            packages.add(match.group(0))
    return packages


def _find_package_version(package: str):
    import importlib.metadata

    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        pass

    module = importlib.import_module(package)

    for v_string in ("__version__", "version"):
        try:
            return getattr(module, v_string)
        except AttributeError:
            pass

    return "unknown"


def _terminal() -> Report:
    import subprocess

    import yuio.io
    import yuio.term

    report = Report("Terminal and CLI")

    term = yuio.io.get_term()
    report.items.append(("interactive support", term.interactive_support.name))
    report.items.append(("terminal colors", term.color_support.name))
    report.items.append(("detected colors", str(term.terminal_theme is not None)))
    report.items.append(("term", os.environ.get("TERM", "")))
    report.items.append(("colorterm", os.environ.get("COLORTERM", "")))
    report.items.append(("shell", os.environ.get("SHELL", "")))
    report.items.append(("ci", str(yuio.term.detect_ci())))

    if os.name != "nt":
        with report_exc(report, "wsl"):
            try:
                wslinfo = subprocess.getoutput("wslinfo --version")
            except FileNotFoundError:
                wslinfo = "None"
            report.items.append(("wsl", wslinfo))

    return report


def print_report(
    *,
    dest: _t.TextIO | None = None,
    settings: ReportSettings | bool | None = None,
    app: yuio.app.App[_t.Any] | None = None,
):
    """
    Collect and print debug report to the given ``dest``.

    :param dest:
        destination stream for printing bug report, default is ``stdout``.
    :param settings:
        settings for bug report generation.
    :param app:
        main app of the project, used to extract project's version and dependencies.

        .. note::

            If your app defined in the ``__main__`` module, Yuio will not be able
            to extract its dependencies and print their versions.

            We recommend defining app in a separate file and importing it to the
            ``__main__`` module.

    """
    if dest is None:
        dest = sys.__stdout__
    if settings is None or isinstance(settings, bool):
        settings = ReportSettings()

    all_collectors: list[tuple[str | None, EnvCollector | Report]] = [
        ("System", _system),
        ("Versions", lambda: _versions(settings, app)),
        ("Terminal and CLI", _terminal),
    ]
    all_collectors.extend(settings.collectors or [])
    all_collectors.extend(_load_env_collectors())

    START = 0
    AFTER_TITLE = 1
    AFTER_ITEM = 2
    AFTER_LONG_ITEM = 3

    position = START

    print("```", file=dest)

    col_width = 20
    indent = " " * (col_width + 2)
    for name, collector in all_collectors:
        printed_title = False
        try:
            name = name or str(collector)
        except:
            name = "Unknown category"
        try:
            if isinstance(collector, Report):
                report = collector
            else:
                report = collector()
            title = report.title or name

            if position in [AFTER_ITEM, AFTER_LONG_ITEM]:
                print("\n", file=dest)
            print(indent + title, file=dest)
            print(indent + "~" * len(title) + "\n", file=dest)
            printed_title = True
            position = AFTER_TITLE

            for data in report.items or ["No data"]:
                if isinstance(data, str):
                    key, value = "", data
                else:
                    key, value = data
                if key:
                    if position == AFTER_LONG_ITEM:
                        print("", file=dest)
                    print(f"{key:>{col_width}}: {value}", file=dest)
                    position = AFTER_ITEM
                else:
                    if position in [AFTER_ITEM, AFTER_LONG_ITEM]:
                        print("", file=dest)
                    print(textwrap.indent(value, indent), file=dest)
                    position = AFTER_LONG_ITEM
        except Exception:
            if not printed_title:
                if position in [AFTER_ITEM, AFTER_LONG_ITEM]:
                    print("\n", file=dest)
                print(indent + name + "\n", file=dest)
                print(indent + "~" * len(name) + "\n", file=dest)
                position = AFTER_TITLE
            if position in [AFTER_ITEM, AFTER_LONG_ITEM]:
                print("", file=dest)
            print(indent + "Error when collecting information:", file=dest)
            print(
                textwrap.indent(traceback.format_exc(), indent).strip("\n"), file=dest
            )
            position = AFTER_LONG_ITEM

    print("```", file=dest)


if __name__ == "__main__":
    print_report()
