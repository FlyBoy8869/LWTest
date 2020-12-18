import sys

TESTING_MODE = True if "DEBUG" in sys.argv else False

version = "0.2.5"

app_title = f"LWTest - v{version}"
if TESTING_MODE:
    app_title += " - TESTING_MODE"
