import re as _re
import sys as _sys
from typing import *  # type: ignore

if TYPE_CHECKING:
    from typing_extensions import Annotated, BinaryIO, Never, TextIO, TypeAlias
else:
    _globals = globals()
    if "TypeAlias" not in _globals:
        TypeAlias = object
    if "Never" not in _globals:
        Never = object
    if "Annotated" not in _globals:
        Annotated = object
    if "TextIO" not in _globals:
        TextIO = object
    if "BinaryIO" not in _globals:
        BinaryIO = object
    del _globals

if TYPE_CHECKING:
    StrRePattern: TypeAlias = _re.Pattern[str]
else:
    try:
        StrRePattern = _re.Pattern[str]
    except TypeError:
        StrRePattern = _re.Pattern

try:
    from typing_extensions import Union as _TypingExtensionsUnion
except ImportError:
    _TypingExtensionsUnion = Union

# Union of this type is created when using `typing.Union`.
_union_origin = get_origin(Union[str, int])
# Union of this type is created when using `typing_extensions.Union`.
_typing_extensions_union_origin = get_origin(_TypingExtensionsUnion[str, int])
# Union of this type is created when using new syntax.
_new_union_origin = (
    get_origin(eval("str | int")) if _sys.version_info >= (3, 10) else _union_origin
)


def is_union(origin: object):
    """Check if a type hint is a union."""
    return (
        origin is _new_union_origin
        or origin is _union_origin
        or origin is _typing_extensions_union_origin
    )


# From python 3.8 typing
__all__ = [
    "Any",
    "Callable",
    "ClassVar",
    "Final",
    "ForwardRef",
    "Generic",
    "Literal",
    "Optional",
    "Protocol",
    "Tuple",
    "Type",
    "TypeVar",
    "Union",
    "AbstractSet",
    "ByteString",
    "Container",
    "ContextManager",
    "Hashable",
    "ItemsView",
    "Iterable",
    "Iterator",
    "KeysView",
    "Mapping",
    "MappingView",
    "MutableMapping",
    "MutableSequence",
    "MutableSet",
    "Sequence",
    "Sized",
    "ValuesView",
    "Awaitable",
    "AsyncIterator",
    "AsyncIterable",
    "Coroutine",
    "Collection",
    "AsyncGenerator",
    "AsyncContextManager",
    "Reversible",
    "SupportsAbs",
    "SupportsBytes",
    "SupportsComplex",
    "SupportsFloat",
    "SupportsIndex",
    "SupportsInt",
    "SupportsRound",
    "ChainMap",
    "Counter",
    "Deque",
    "Dict",
    "DefaultDict",
    "List",
    "OrderedDict",
    "Set",
    "FrozenSet",
    "NamedTuple",
    "TypedDict",
    "Generator",
    "AnyStr",
    "cast",
    "final",
    "get_args",
    "get_origin",
    "get_type_hints",
    "NewType",
    "no_type_check",
    "no_type_check_decorator",
    "NoReturn",
    "overload",
    "runtime_checkable",
    "Text",
    "TYPE_CHECKING",
    # Additional
    "Annotated",
    "TypeAlias",
    "Never",
    "is_union",
    "TextIO",
    "BinaryIO",
]
