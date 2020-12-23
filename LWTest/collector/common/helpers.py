def get_columns(driver):
    return 6 if "phase 4" in driver.page_source.lower() else 3


def get_elements(selector, driver):
    return driver.find_elements_by_css_selector(selector)


def enter_constants(fields, value):
    for field in fields:
        set_field(field, value)


def set_field(field, value):
    field.clear()
    field.send_keys(value)
