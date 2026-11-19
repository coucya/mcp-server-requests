import unittest

from .ua import UA_FILE, UALoader


class TestUALoaderFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = UALoader(UA_FILE)

    def test_filter_by_browser(self):
        items = self.loader.filter(browser="chrome")
        self.assertTrue(items)
        self.assertTrue(all(item["browser"].lower() == "chrome" for item in items))

    def test_filter_by_os(self):
        items = self.loader.filter(os="windows")
        self.assertTrue(items)
        self.assertTrue(all(item["os"].lower() == "windows" for item in items))

    def test_filter_by_browser_and_os(self):
        items = self.loader.filter(browser="chrome", os="windows")
        self.assertTrue(items)
        self.assertTrue(all(item["browser"].lower() == "chrome" for item in items))
        self.assertTrue(all(item["os"].lower() == "windows" for item in items))

    def test_filter_no_match(self):
        self.assertEqual(self.loader.filter(browser="chrome", os="plan9"), [])


if __name__ == '__main__':
    unittest.main()
