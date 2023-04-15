import typing as _t

T = _t.TypeVar('T')

# class LenGtMeta(type):
#     def __rmatmul__(cls, value: _t.Type[T]) -> _t.Type[T]:
#         return _t.Annotated[value, cls]

# class LenGt(metaclass=LenGtMeta):
#     def __class_getitem__(cls, params: int):
#         class _LenGtAlias(LenGt):
#             _params = params
#         return _LenGtAlias

# def m() -> _t.Any: ...

# x: list[int] @ LenGt['as'] = m()
# # print(list[int] @ LenGt['as'])



import yuio.parse

class List(_t.Generic[T]):
    def __class_getitem__(cls, params) -> _t.Type[list]: ...


x: List[int, 0] = ''
