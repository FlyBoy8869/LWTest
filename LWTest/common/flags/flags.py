from dataclasses import dataclass
import functools
from enum import Enum
from typing import List, Optional


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


def flags(*, read: Optional[List[str]] = None,
          set_: Optional[List[str]] = None,
          clear: Optional[List[str]] = None):

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
