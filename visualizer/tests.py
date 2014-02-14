import unittest
import logging
import sys
from visualizer.plugin import load
from visualizer.plugin.attribute import color

class TestPlugins(unittest.TestCase):
    def setUp(self):
        pass

    def test_normal(self):
        plugin, module = load('test/normal')
        self.assertIsNotNone(plugin)
        self.assertIsNotNone(module)

    def test_missing_deps(self):
        plugin, module = load('test/missing_deps')
        self.assertIsNone(plugin)
        self.assertIsNone(module)

    def test_invalid_meta(self):
        plugin, module = load('test/invalid_meta')
        self.assertIsNone(plugin)
        self.assertIsNone(module)

class TestColor(unittest.TestCase):
    def test_tuple_rgb(self):
        c = color('(0,1,2)')
        self.assertEqual(c[0], 0)
        self.assertEqual(c[1], 1)
        self.assertEqual(c[2], 2)

    def test_tuple_rgba(self):
        c = color('(0,1,2,3)')
        self.assertEqual(c[0], 0)
        self.assertEqual(c[1], 1)
        self.assertEqual(c[2], 2)
        self.assertEqual(c[3], 3)

    def test_hex_rgb(self):
        c = color('#001122')
        self.assertEqual(c[0], int('0x00',16) / 255.0)
        self.assertEqual(c[1], int('0x11',16) / 255.0)
        self.assertEqual(c[2], int('0x22',16) / 255.0)

    def test_hex_rgb_short(self):
        c = color('#012')
        self.assertEqual(c[0], int('0x00',16) / 255.0)
        self.assertEqual(c[1], int('0x11',16) / 255.0)
        self.assertEqual(c[2], int('0x22',16) / 255.0)

    def test_hex_rgba(self):
        c = color('#001122ee')
        self.assertEqual(c[0], int('0x00',16) / 255.0)
        self.assertEqual(c[1], int('0x11',16) / 255.0)
        self.assertEqual(c[2], int('0x22',16) / 255.0)
        self.assertEqual(c[3], int('0xee',16) / 255.0)

    def test_hex_rgba_short(self):
        c = color('#012e')
        self.assertEqual(c[0], int('0x00',16) / 255.0)
        self.assertEqual(c[1], int('0x11',16) / 255.0)
        self.assertEqual(c[2], int('0x22',16) / 255.0)
        self.assertEqual(c[3], int('0xee',16) / 255.0)

def run():
    ch = logging.StreamHandler()
    ch.setLevel(logging.CRITICAL)
    log = logging.getLogger('')
    log.addHandler(ch)
    log.setLevel(logging.CRITICAL)

    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if len(result.errors) > 0: sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    run()
