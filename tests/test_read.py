from collections import namedtuple
from unittest import TestCase

import LWTest.collector.read.read as collector_read

from LWTest.collector.read.read import DataReader


class Element:
    def __init__(self, value):
        self._value = value

    def get_attribute(self, _):
        return self._value


class TestDataReader(TestCase):
    def setUp(self) -> None:
        self.data_reader = DataReader("", "")

    def test__scrape_readings(self):
        class TextContentElement(Element):
            """contents are retrieved using element.get_attribute('textContent')"""
            pass

        elements = [
            TextContentElement("Charles"),
            TextContentElement("Domenic"),
            TextContentElement("Cognato"),
            TextContentElement("Jr.")
        ]
        content = self.data_reader._scrape_readings(elements, "textContent", 0, len(elements))
        self.assertEqual(["Charles", "Domenic", "Cognato", "Jr."], content, "Not equal")

    def test__massage_real_power_readings(self):
        real_power_elements = ["1490.40", "1491.50", "1489.30"]
        massaged_readings = self.data_reader._massage_real_power_readings(real_power_elements)
        self.assertEqual(["1490400", "1491500", "1489300"], massaged_readings, "Not equal")

    def test__extract_advanced_readings(self):
        class ValueElement(Element):
            """values are retrieved using element.get_attribute('value')"""
            pass

        readings = [
            ValueElement("0.02525"), ValueElement("0.02526"), ValueElement("0.02527"),
            ValueElement("1.50000"), ValueElement("1.51010"), ValueElement("1.52020"),
            ValueElement("Filler"), ValueElement("Filler"), ValueElement("Filler"),
            ValueElement("Filler"), ValueElement("Filler"), ValueElement("Filler"),
            ValueElement("0.0"), ValueElement("1.1"), ValueElement("2.2")
        ]

        expected = [
            ["0.02525", "0.02526", "0.02527"],
            ["1.50000", "1.51010", "1.52020"],
            ["0.0", "1.1", "2.2"]
        ]
        self.assertEqual(expected, self.data_reader._extract_advanced_readings(readings, 3), "Not equal")


class TestStandAloneFunctions(TestCase):
    Driver = namedtuple("Driver", "page_source")

    def setUp(self) -> None:
        self.driver_6_column = self.Driver(page_source="Phase 4")
        self.driver_3_column = self.Driver(page_source="No Phase info here.")

    def test__find_all_indexes_of_na_in_list(self):
        values = ["Value1", "NA", "Value2", "Value3", "NA", "NA"]
        self.assertEqual([1, 4, 5], collector_read._find_all_indexes_of_na_in_list(values))

    def test__get_columns_is_6(self):
        self.assertEqual(6, collector_read._get_columns(self.driver_6_column))

    def test__get_columns_is_3(self):
        self.assertEqual(3, collector_read._get_columns(self.driver_3_column))
