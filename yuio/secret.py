# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Utility types for working with secret data.


.. autoclass:: SecretValue
    :members:

.. type:: SecretString
    :canonical: SecretValue[str]

    Convenience alias for secret strings.

"""

from __future__ import annotations

from dataclasses import dataclass

from yuio import _typing as _t

__all__ = [
    "SecretString",
    "SecretValue",
]

T = _t.TypeVar("T", covariant=True)


@dataclass(frozen=True, unsafe_hash=True, slots=True)
class SecretValue(_t.Generic[T]):
    """
    A simple wrapper that prevents inner value from accidentally leaking to logs
    or messages: it returns ``"***"`` when converted to string via
    :class:`str() <str>` or :func:`repr`.

    """

    data: T
    """
    Secret data.

    """

    def __str__(self) -> str:
        return "***"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(***)"


SecretString: _t.TypeAlias = SecretValue[str]
"""
Convenience alias for secret string.

"""
