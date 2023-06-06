from environment import Environment
import unittest
from time import sleep


class Test(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = Environment()

    def setUp(self):
        self.env.start()
        sleep(2)  # allow svxlink and remotes to start up FIXME: detect this

    def tearDown(self):
        self.env.stop()

    def test_switchover_by_squelch(self):
        self.env.open_squelch("remote1")
        self.assertEqual(self.env.wait_for_ptt(True, 5), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_active("remote1", True, 5), True, "remote1 should become active")
        self.env.open_squelch("remote2")
        self.assertEqual(self.env.wait_for_remote_active("remote2", True, 5), False, "remote2 should still be off, as remote1 is still active")
        self.env.open_squelch("remote1", False)
        self.assertEqual(self.env.wait_for_remote_active("remote2", True, 5), True, "remote1 squelch is closed, remote2 should take over")


if __name__ == '__main__':
    unittest.main()
