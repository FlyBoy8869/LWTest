class Result:
    def __init__(self, success, value, error=None):
        self._success = success
        self._value = value
        self._error = error

    @property
    def success(self):
        return self._success

    @property
    def value(self):
        return self._value

    @property
    def error(self):
        return self._error

    def __bool__(self):
        if self._success:
            return True

        return False
