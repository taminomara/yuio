import functools

class A:
    __actual_cls__: type | None = None

    def __init_subclass__(cls):
        if "__init__" not in cls.__dict__:
            return

        init = cls.__init__
        @functools.wraps(init)
        def _wrapped_init(self, *args, **kwargs):
            prev_actual_cls, self.__actual_cls__ = self.__actual_cls__, cls
            try:
                init(self)
            finally:
                self.__actual_cls__ = prev_actual_cls
        cls.__init__ = _wrapped_init


class B(A):
    def __init__(self) -> None:
        super().__init__()
        print(self.__actual_cls__)

class C(B):
    def __init__(self) -> None:
        super().__init__()
        print(self.__actual_cls__)


print(C.__init__, C().__init__)
