from typeguard import typechecked
from types import FunctionType
from abc import ABCMeta


class TypeCheckedMeta(type):
    def __new__(cls, name, bases, dct):
        new_dct = {k: typechecked(v) if isinstance(v, FunctionType) else v for k, v in dct.items()}
        return super().__new__(cls, name, bases, new_dct)


class CombinedMeta(ABCMeta, TypeCheckedMeta):
    pass


class TypeCheckBase(metaclass=CombinedMeta):
    pass
