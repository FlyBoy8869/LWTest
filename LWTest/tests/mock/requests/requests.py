import copy
import random

_page = None
_MAX_LINES_TO_ADD = 1


class _Page:
    def __init__(self, contents: str):
        self._simulated_text = ""
        self._simulated_status_code = 200
        self._current_index = 0

        with open(contents, 'r') as in_f:
            self._doc = in_f.readlines()
            self._doc.reverse()

    @property
    def text(self):
        return self._simulated_text

    @property
    def status_code(self):
        return self._simulated_status_code

    def add_more_lines(self):
        number_of_lines = random.randint(0, _MAX_LINES_TO_ADD)

        while self._current_index + number_of_lines > len(self._doc):
            number_of_lines -= 1

        for i in range(number_of_lines):
            self._simulated_text += self._doc[self._current_index + i]

        self._current_index += number_of_lines


def _setup_page(contents: str):
    global _page
    _page = _Page(contents)


def get(url: str, timeout=1):
    if _page is None:
        _setup_page(url)

    page = copy.deepcopy(_page)
    _page.add_more_lines()

    return page
