from LWTest.common import oscomp
from LWTest.common.oscomp import OSBrand

chromedriver_path: str = ""
if oscomp.os_brand == OSBrand.WINDOWS:
    chromedriver_path = "LWTest/resources/drivers/chromedriver/windows/version-83_0_4103_39/chromedriver.exe"
elif oscomp.os_brand == OSBrand.MAC:
    chromedriver_path = "LWTest/resources/drivers/chromedriver/macos/version-83_0_4103_39/chromedriver"
elif oscomp.os_brand == OSBrand.LINUX:
    chromedriver_path = "LWTest/resources/drivers/chromedriver/linux/version-83_0_4103_39/chromedriver"
