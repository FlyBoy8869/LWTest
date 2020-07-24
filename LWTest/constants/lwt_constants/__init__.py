import LWTest

from .constants import *
from .sensor_table_columns import TableColumn
from .tolerance import Tolerance

TESTING_MODE = LWTest.TESTING_MODE

if TESTING_MODE:
    from .debug_urls import *
    from .debug_timeouts import *
else:
    from .release_urls import *
    from .release_timeouts import *
