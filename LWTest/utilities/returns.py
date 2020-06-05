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
        assert False, "You must test for Result.success."


if __name__ == '__main__':
    result = Result(True, "6969")

    if result.success:
        print(f"The result of testing 'result.success' is {result.value}.")

    if result:
        print("This should not print.")
