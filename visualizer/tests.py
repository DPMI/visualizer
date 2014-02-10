import unittest
import logging
import sys
from visualizer.plugin import load

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

def run():
    ch = logging.StreamHandler()
    ch.setLevel(logging.CRITICAL)
    log = logging.getLogger('')
    log.addHandler(ch)
    log.setLevel(logging.CRITICAL)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPlugins)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if len(result.errors) > 0: sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    run()
