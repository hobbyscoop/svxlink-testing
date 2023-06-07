"""
This file tests the functions that we did not patch. Just to make sure these still work correctly
"""
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
        """
        the voter should switch over to the other active remote, after the first one closes the squelch
        """
        self.env.open_squelch("remote1")
        self.assertEqual(self.env.wait_for_ptt(True, 5), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, 5), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", 5), True, "[initial] remote1 should be audible")
        self.env.open_squelch("remote2")
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, 5), False, "remote2 should still be off, as remote1 is still active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", 5), True, "[continue] remote1 should still be audible")
        self.env.open_squelch("remote1", False)
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, 5), True, "remote1 squelch is closed, remote2 should take over")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", 5), True, "[switchover] remote2 should now be audible")

    def test_switchover_by_siglev(self):
        """
        the voter should switch over to the remote which is louder (in siglev)
        """
        self.env.open_squelch("remote2")
        self.assertEqual(self.env.wait_for_ptt(True, 5), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, 5), True, "remote2 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", 5), True, "remote2 should be audible")
        self.env.open_squelch("remote1")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, 5), True, "remote1 become active, as it's louder")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", 5), True, "remote1 should be audible")

    def test_switchback_by_siglev(self):
        """
        the voter should switch over to the remote which is louder (in siglev)
        """
        self.env.open_squelch("remote2")
        self.assertEqual(self.env.wait_for_ptt(True, 5), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, 5), True, "remote2 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", 5), True, "[initial] remote2 should be audible")
        self.env.open_squelch("remote1")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, 5), True, "remote1 become active, as it's louder")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", 5), True, "[switchover] remote1 should be audible")
        self.env.open_squelch("remote1", False)
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, 5), True, "voter should fall back to remote2")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", 5), True, "[fallback] remote2 should be audible")


if __name__ == '__main__':
    unittest.main()
