import sys

TESTING_MODE = True if "DEBUG" in sys.argv else False

version = "0.2.4"

app_title = "LWTest"
if TESTING_MODE:
    app_title += " - TESTING_MODE"
