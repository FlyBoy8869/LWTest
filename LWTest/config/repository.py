from enum import Enum


class ConfigItem(Enum):
    TESTING = "testing"


class _ConfigurationRepository:
    def __getattr__(self, item):
        return self.__dict__[item] if item in self.__dict__ else None

    def __setattr__(self, key, value):
        self.__dict__[key] = value


if __name__ == '__main__':
    cr = _ConfigurationRepository()
    if cr.something:
        print("found it")
    else:
        print("not there")
    cr.something = "something"
    print(cr.something)
