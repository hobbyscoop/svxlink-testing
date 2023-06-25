"""
This file tests the functions that we did not patch. Just to make sure these still work correctly
"""
from environment import Environment
import logging
import unittest

WAIT_TIME = 5


class Test(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = Environment()
        self.log = logging.getLogger(__class__.__name__)

    def setUp(self):
        if not self.env.start():
            raise RuntimeError("failed to set up env")

    def tearDown(self):
        self.log.getChild("voter").info(self.env.voter_state)
        self.log.getChild("ptt").info(self.env.ptt_state)
        self.env.stop()

    def test_switchover_with_squelch(self):
        """
        When a receiver with higher siglev opens its squelch, the voter should switch over to that receiver
        """
        self.env.open_squelch("remote2", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, WAIT_TIME), True, "remote2 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", WAIT_TIME), True, "remote2 should be audible")
        # open remote1 with higher siglev, so voter switches to it
        self.env.open_squelch("remote1", True)
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 become active, as it's louder")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")

    def test_dont_switchover_with_squelch(self):
        """
        When a receiver with lower siglev opens its squelch, the voter should not switch over to that receiver
        """
        self.env.open_squelch("remote1", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        # open remote2 with lower siglev
        self.env.open_squelch("remote2", True)
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should stay active, as it's louder")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should still be audible")

    def test_switchback_to_higher_with_squelch(self):
        """
        When two receivers are open, and the one with the lower siglev closes,
        the voter should stay with the one with the higher siglev.
        """
        self.env.open_squelch("remote1", True)
        self.env.open_squelch("remote2", True)
        # remote1 should be active, as it has higher siglev
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        self.env.open_squelch("remote2", False)
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should still be active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should still be audible")

    def test_switchback_to_lower_with_squelch(self):
        """
        When two receivers are open, and the one with the higher siglev closes,
        the voter should switch to the one with the lower siglev.
        """
        self.env.open_squelch("remote1", True)
        self.env.open_squelch("remote2", True)
        # remote1 should be active, as it has higher siglev
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        self.env.open_squelch("remote1", False)
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, WAIT_TIME), True, "remote1 squelch is closed, remote2 should take over")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", WAIT_TIME), True, "remote2 should now be audible")

    def test_disable_deselect_off(self):
        """
        the voter should deselect a receiver that is disabled, and shut TX of if there's no other receivers left
        """
        self.env.open_squelch("remote1", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        # disable remote1, should turn off TX
        self.env.disable_remote("remote1")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "enabled", False, WAIT_TIME), True, "remote1 should become disabled")
        self.assertEqual(self.env.wait_for_ptt(False, WAIT_TIME*4), True, "transmitter should be off")

    def test_disable_deselect_switchover(self):
        """
        the voter should switch over to another receiver when the active receiver is disabled
        """
        self.env.open_squelch("remote1", True)  # remote1 has higher siglev, so it's selected
        self.env.open_squelch("remote2", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        # disable the strongest remote1, so voter falls back to weaker remote2
        self.env.disable_remote("remote1")
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, WAIT_TIME*2), True, "remote2 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", WAIT_TIME), True, "remote2 should be audible")

    def test_select_disable_open_enable(self):
        """
        the voter should select a receiver if it's disabled, opened and enabled
        """
        self.env.disable_remote("remote1")
        self.env.open_squelch("remote1", True)
        self.env.enable_remote("remote1")
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")

    def test_reselect_open_disable_enable(self):
        """
        the voter should reselect if an open remote is enabled after disable

        This currently doesn't work, as the squelch is forced to be closed when a receiver is disabled.
        So it needs the squelch of the disabled receiver to toggle.
        """
        self.env.open_squelch("remote1", True)
        self.env.disable_remote("remote1")
        self.assertEqual(self.env.wait_for_ptt(False, WAIT_TIME*2), True, "transmitter should be off")
        self.env.enable_remote("remote1")
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")

    def test_reselect_open_disable_enable_interrupt(self):
        """
        the voter should reselect a receiver that is disabled and then enabled, if another receiver was selected during disable

        This currently doesn't work, as the squelch is forced to be closed when a receiver is disabled.
        So it needs the squelch of the disabled receiver to toggle.
        """
        self.env.open_squelch("remote1", True)
        self.env.open_squelch("remote2", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        # disable remote1, remote2 takes over
        self.env.disable_remote("remote1")
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, WAIT_TIME), True, "remote2 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", WAIT_TIME), True, "remote2 should be audible")
        # enable remote1, voter should switch back
        self.env.enable_remote("remote1")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")


if __name__ == '__main__':
    unittest.main()
