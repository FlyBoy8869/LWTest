from linewatchshared import oscomp
from linewatchshared.oscomp import OSBrand

CHROMEDRIVER_PATH: str = ""
if oscomp.os_brand == OSBrand.MAC:
    CHROMEDRIVER_PATH = r"LWTest/resources/drivers/chromedriver/macos/version_83-0-4103-39/chromedriver"
elif oscomp.os_brand == OSBrand.WINDOWS:
    CHROMEDRIVER_PATH = r"LWTest/resources/drivers/chromedriver/windows/version_83-0-4103-39/chromedriver.exe"
elif oscomp.os_brand == OSBrand.LINUX:
    CHROMEDRIVER_PATH = r"LWTest/resources/drivers/chromedriver/linux/version_83-0-4103-39/chromedriver"
else:
    raise RuntimeError("LWTest does not support chromedriver on your OS.")