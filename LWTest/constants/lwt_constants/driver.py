from LWTest.utilities import oscomp
from LWTest.utilities.oscomp import OSBrand

CHROMEDRIVER_PATH: str = ""
if oscomp.os_brand == OSBrand.MAC:
    CHROMEDRIVER_PATH = r"LWTest/resources/drivers/chromedriver/macos/version_87/chromedriver"
elif oscomp.os_brand == OSBrand.WINDOWS:
    CHROMEDRIVER_PATH = r"LWTest/resources/drivers/chromedriver/windows/version_83/chromedriver.exe"
elif oscomp.os_brand == OSBrand.LINUX:
    CHROMEDRIVER_PATH = r"LWTest/resources/drivers/chromedriver/linux/version_83/chromedriver"
else:
    raise RuntimeError("LWTest does not support chromedriver on your OS.")
