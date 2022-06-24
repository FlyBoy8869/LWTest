import sys

TESTING_MODE = "DEBUG" in sys.argv

version = "0.3.6"

app_title = f"LWTest - v{version}"
if TESTING_MODE:
    app_title += " - TESTING_MODE"
