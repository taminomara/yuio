# Based on disjoint-set by Maciej Rapacz, MIT license.
# See https://github.com/mrapacz/disjoint-set
#
# Changes: added "insert" operation, added union by size optimization.

import collections
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


T = _t.TypeVar("T")


class DisjointSet(_t.Generic[T]):
    def __init__(self, *args, **kwargs) -> None:
        self._data: dict[T, tuple[T, int]] = {}

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, item: T) -> bool:
        return item in self._data

    def __bool__(self) -> bool:
        return bool(self._data)

    def __getitem__(self, element: T) -> T:
        return self.find(element)

    def __eq__(self, other: _t.Any) -> bool:
        if not isinstance(other, DisjointSet):
            return NotImplemented

        return self._data == other._data

    def __repr__(self) -> str:
        sets = {key: val for key, val in self}
        return f"{self.__class__.__name__}({sets})"

    def __str__(self) -> str:
        return "{classname}({values})".format(
            classname=self.__class__.__name__,
            values=", ".join(str(dset) for dset in self.itersets()),
        )

    def __iter__(self) -> _t.Iterator[tuple[T, T]]:
        for key in self._data.keys():
            yield key, self.find(key)

    def add(self, x: T):
        if x in self._data:
            raise RuntimeError("already inserted")
        self._data[x] = (x, 1)

    def find(self, x: T) -> T:
        return self._find(x)[0]

    def _find(self, x: T) -> tuple[T, int]:
        while x != self._data[x][0]:
            self._data[x] = self._data[self._data[x][0]]
            x = self._data[x][0]
        return self._data[x]

    def union(self, x: T, y: T) -> None:
        parent_x, size_x = self._find(x)
        parent_y, size_y = self._find(y)
        if parent_x != parent_y:
            if size_x >= size_y:
                parent = parent_y
            else:
                parent = parent_x
            self._data[parent_x] = self._data[parent_y] = parent, size_x + size_y

    def connected(self, x: T, y: T) -> bool:
        return self.find(x) == self.find(y)

    def itersets(self) -> _t.Iterator[set[T]]:
        element_classes: collections.defaultdict[T, set[T]] = collections.defaultdict(set)
        for element in self._data:
            element_classes[self.find(element)].add(element)
        yield from element_classes.values()
