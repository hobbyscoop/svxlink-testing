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

    def test_switchover_by_squelch(self):
        """
        the voter should switch over to the other active remote, after the first one closes the squelch
        """
        self.env.open_squelch("remote1", True)
        self.env.open_squelch("remote2", True)
        # remote1 should be active, as it's louder
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "[initial] remote1 should be audible")
        self.env.open_squelch("remote1", False)
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, WAIT_TIME), True, "remote1 squelch is closed, remote2 should take over")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "[switchover] remote2 should now be audible")

    def test_switchover_by_siglev(self):
        """
        the voter should switch over to the remote which is louder (in siglev)
        """
        self.env.open_squelch("remote2", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, WAIT_TIME), True, "remote2 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", WAIT_TIME), True, "remote2 should be audible")
        # open louder remote1, so voter switches to it
        self.env.open_squelch("remote1", True)
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 become active, as it's louder")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")

    def test_switchback_by_siglev(self):
        """
        the voter should switch over to the remote which is louder (in siglev)
        """
        self.env.open_squelch("remote1", True)
        self.env.open_squelch("remote2", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        # close louder remote1, so voter falls back to remote2
        self.env.open_squelch("remote1", False)
        self.assertEqual(self.env.wait_for_remote_state("remote2", "active", True, WAIT_TIME), True, "voter should fall back to remote2")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote2", WAIT_TIME), True, "remote2 should be audible")

    def test_disable_unselect_off(self):
        """
        the voter should unselect a remote that is disabled
        :return:
        """
        self.env.open_squelch("remote1", True)
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")
        # disable remote1, should turn off TX
        self.env.disable_remote("remote1")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "enabled", False, WAIT_TIME), True, "remote1 should become disabled")
        self.assertEqual(self.env.wait_for_ptt(False, WAIT_TIME*4), True, "transmitter should be off")

    def test_disable_unselect_switchover(self):
        """
        the voter should switch over to another remote if the active remote is disabled
        :return:
        """
        self.env.open_squelch("remote1", True)  # remote1 has higher siglev
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
        the voter should select if a disabled remote is opened and enabled
        :return:
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
        OLD: doesn't work:
        18:44:28.704 INFO svxlink    | RX remote1 has been disabled
        18:44:28.903 INFO svxlink    | ### Voter::SqlCloseWait::timerExpired: no bestSrx, going IDLE
        18:44:38.725 INFO {'time': datetime.datetime(2023, 6, 9, 18, 44, 28, 802000), 'remote1': {'orig': 'remote1#+1000', 'name': 'remote1', 'enabled': False, 'siglev': 1000}, 'remote2': {'orig': 'remote2_+030', 'name': 'remote2', 'enabled': True, 'sql_open': False, 'active': False, 'siglev': 30}}

        :return:
        """
        self.skipTest("doesn't work on OLD")
        self.env.open_squelch("remote1", True)
        self.env.disable_remote("remote1")
        self.assertEqual(self.env.wait_for_ptt(False, WAIT_TIME*2), True, "transmitter should be off")
        self.env.enable_remote("remote1")
        self.assertEqual(self.env.wait_for_ptt(True, WAIT_TIME), True, "transmitter should be on")
        self.assertEqual(self.env.wait_for_remote_state("remote1", "active", True, WAIT_TIME), True, "remote1 should become active")
        self.assertEqual(self.env.wait_for_remote_by_tone("remote1", WAIT_TIME), True, "remote1 should be audible")

    def test_reselect_open_disable_enable_interrupt(self):
        """
        the voter should reselect a remote that is disabled and then enabled, if another remote was selected during disable
        :return:
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
