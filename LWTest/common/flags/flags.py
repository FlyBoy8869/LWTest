from dataclasses import dataclass
import functools
from enum import Enum
from typing import List


class FlagsEnum(Enum):
    SERIALS: str = "serials"
    ADVANCED: str = "advanced"
    CALIBRATE: str = "calibrate"
    CORRECTION: str = "correction"

    def __eq__(self, other):
        assert type(other) == str, f"invalid type: {type(other)}, must be {type('str')}"
        return self.value == other


@dataclass
class Flags:
    serials: bool = False
    advanced: bool = False
    calibrate: bool = False
    correction: bool = False

    def is_set(self, flag: str):
        return self[flag] is True

    def set_flag(self, flag: str):
        self.__dict__[flag] = True

    def __getitem__(self, item):
        return self.__dict__[item]

    def __setitem__(self, key, value):
        self.__dict__[key] = value


managed_flags = Flags()


def flags(*, read: List[FlagsEnum] = None, set_: List[FlagsEnum] = None, clear: List[FlagsEnum] = None):
    def outer(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if read:
                for flag in read:
                    if managed_flags[flag.value] is False:
                        return

            if set_:
                for flag in set_:
                    managed_flags[flag.value] = True

            if clear:
                for flag in clear:
                    managed_flags[flag.value] = False

            result = func(self, *args, *kwargs)

            return result
        return wrapper
    return outer


if __name__ == '__main__':
    mf = Flags()
    print(f"value of 'serials': {mf['serials']}")
    print(f"Is 'serials' set: {mf.is_set('serials')}")

    mf.set_flag("serials")
    print(f"Is 'serials' set: {mf.is_set('serials')}")

    5 == FlagsEnum.SERIALS
