import copy
import random

_page = None
_MAX_LINES_TO_ADD = 1


class _Page:
    def __init__(self, contents: str):
        self._simulated_text = []
        self._simulated_status_code = 200
        self._current_index = 0

        with open(contents, 'r') as in_f:
            self._doc = in_f.readlines()

        self._tail_clutter = self._doc[-55:]
        self._doc = self._doc[:-55]

        self._simulated_text.append(self._doc[0])
        self._current_index = 1

    @property
    def text(self):
        copy_of_text = self._simulated_text.copy()
        self._add_tail_clutter(copy_of_text)
        return "".join(copy_of_text)

    @property
    def status_code(self):
        return self._simulated_status_code

    def add_more_lines(self):
        number_of_lines = random.randint(1, _MAX_LINES_TO_ADD)

        while self._current_index + number_of_lines > len(self._doc):
            number_of_lines -= 1

        for i in range(number_of_lines):
            self._simulated_text.append(self._doc[self._current_index + i])

        self._current_index += number_of_lines

    def _add_tail_clutter(self, buffer):
        buffer.extend(self._tail_clutter)


def _setup_page(contents: str):
    global _page
    _page = _Page(contents)


def get(url: str, timeout=1):
    if _page is None:
        _setup_page(url)

    _page.add_more_lines()
    page = copy.deepcopy(_page)

    return page
