"""
This module wraps around docker-compose and the various svxlink interfaces.
It allows to control the remotes and voter, get statuses, and stop and start the containers.
"""
from datetime import datetime
import docker
import json
import os
import logging
import re
import select
from subprocess import check_output, PIPE, Popen
from threading import Thread
from time import sleep


class Environment:
    remote_tones = {
        300: "remote1",
        600: "remote2",
    }
    compose_logger_process = None

    def __init__(self):
        self.log = logging.getLogger(__class__.__name__)
        self.client = docker.from_env()
        self.branch = os.environ.get("BRANCH", "hobbyscoop")

    def compose_logger(self):
        """
        prints the output of the containers into the log
        :return:
        """
        with Popen(["docker-compose", "logs", "-f", "--no-color"], stdout=PIPE, universal_newlines=True) as proc:
            self.log.info("Started log tailing")
            while proc.poll() is None:
                # use select to check if there is data available to read
                readable, _, _ = select.select([proc.stdout], [], [], 0)
                if proc.stdout in readable:
                    # read and print all available output
                    for line in iter(proc.stdout.readline, ''):
                        self.log.getChild("docker-compose").info(line.strip())

    def start(self):
        """
        start the environment
        :return:
        """
        self.log.info("starting instances")
        if self.running > 0:
            self.log.warning("instances already running, stopping them first")
            self.stop()
        self.log.debug("running docker-compose up -d")
        check_output(["docker-compose", "-f", "docker-compose.yaml", "-f", "docker-compose-{}.yaml".format(self.branch), "up", "-d", "remote1"])
        check_output(["docker-compose", "-f", "docker-compose.yaml", "-f", "docker-compose-{}.yaml".format(self.branch), "up", "-d", "remote2"])
        check_output(["docker-compose", "-f", "docker-compose.yaml", "-f", "docker-compose-{}.yaml".format(self.branch), "up", "-d", "svxlink"])
        self.compose_logger_process = Thread(target=self.compose_logger)
        self.compose_logger_process.start()
        while self.running != 3:
            self.log.debug("waiting for containers to start...")
            sleep(1)

        # start sidecars
        self.start_pty_forwarder("state")
        self.start_pty_forwarder("ptt")
        self.containers["svxlink"].exec_run("/usr/bin/python3 /goertzel.py", detach=True)

        self.log.info("waiting for remotes to connect")
        if not self.wait_for_find_in_logs("svxlink", "172.17.0.1:5211: RemoteTrx protocol", 5):
            self.log.error("timeout waiting for remote1 to connect to svxlink")
            return False
        if not self.wait_for_find_in_logs("svxlink", "172.17.0.1:5212: RemoteTrx protocol", 5):
            self.log.error("timeout waiting for remote1 to connect to svxlink")
            return False
        self.log.info("startup done")
        return True

    def find_in_logs(self, container: str, term: str):
        logs = check_output(["docker-compose", "logs", "--no-color", "--no-log-prefix", container])
        return logs.find(bytes(term, 'utf-8'))

    def wait_for_find_in_logs(self, container: str, term: str, timeout: int):
        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            if self.find_in_logs(container, term):
                return True
        return False

    @property
    def running(self):
        """
        check for all containers to be running
        :return: the number of containers with status running
        """
        return sum([c[1].status == "running" for c in self.containers.items()])

    def stop(self):
        self.log.info("stopping instances")
        check_output(["docker-compose", "down"])

    @property
    def containers(self):
        """
        presents a dict of containers, indexed by their names
        :return:
        """
        containers = self.client.containers.list()
        result = dict()
        for container in containers:
            result[container.name] = container
        return result

    def start_pty_forwarder(self, name):
        """
        the PTY forwarder will read from the fifo and write to a normal file,
        so we can expose the data outside of docker
        :param name:
        :return:
        """
        self.log.debug("starting pty forwarder for {}".format(name))
        self.containers["svxlink"].exec_run("/bin/bash -c \"cat /dev/shm/{name} > /{name}\"".format(name=name), detach=True)

    def open_squelch(self, name, state=True):
        if state:
            state = "O"
        else:
            state = "Z"
        self.log.info("setting squelch for {} to {}".format(name, state))
        self.containers[name].exec_run("/bin/bash -c \"echo {state} > /tmp/sql\"".format(state=state))

    def enable_remote(self, name):
        self.log.info("enabling {}".format(name))
        if os.environ.get("BRANCH") == "old":
            self.containers["svxlink"].exec_run("/bin/bash -c \"echo {name}:1 > /dev/shm/voter\"".format(name=name))
        else:
            self.containers["svxlink"].exec_run("/bin/bash -c \"echo ENABLE {name} > /dev/shm/voter\"".format(name=name))

    def disable_remote(self, name):
        self.log.info("disabling {}".format(name))
        if os.environ.get("BRANCH") == "old":
            self.containers["svxlink"].exec_run("/bin/bash -c \"echo {name}:0 > /dev/shm/voter\"".format(name=name))
        else:
            self.containers["svxlink"].exec_run("/bin/bash -c \"echo MUTE {name} > /dev/shm/voter\"".format(name=name))

    def reset(self):
        self.log.info("resetting test env")
        self.open_squelch("remote1", False)
        self.open_squelch("remote2", False)
        self.enable_remote("remote1")
        self.enable_remote("remote2")

    @property
    def ptt_state(self):
        """
        returns the last known state of the transmitter:
        - on: True
        - off: False
        - unknown: None
        :return:
        """
        with open("ptt", "r") as ptt_file:
            data = ptt_file.read()
            if not data:
                return None
            state = data[-1]
            if state == "T":
                return True
            if state == "R":
                return False
            return None

    def wait_for_ptt(self, state: bool, timeout: int):
        """
        wait for a transmitter state, with a timeout
        :param state:
        :param timeout:
        :return:
        """
        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            if self.ptt_state == state:
                return True
        return False

    def parse_old_state(self, data):
        """
        Try to parse the state info in the old format, or raise an exception
        :param data:
        :return:
        """
        status_options = {
            "_": "closed",
            ":": "open",
            "*": "active",
            "#": "off",
        }
        # old format support: remote1*+1000 remote2_+030
        # "_": "closed",
        # ":": "open",
        # "*": "active",
        # "#": "off",
        # new format: {'active': False, 'enabled': True, 'id': '?', 'name': 'remote1', 'siglev': 0, 'sql_open': False}
        states = []
        for item in data.split(' '):
            if len(item) < 4:
                break
            state = {"orig": item}
            remote, info = re.split(r'[_:#*]', item)
            state["name"] = remote
            status = item[len(remote):len(remote)+1]
            if status == "_":
                state["enabled"] = True
                state["sql_open"] = False
                state["active"] = False
            elif status == ":":
                state["enabled"] = True
                state["sql_open"] = True
                state["active"] = False
            elif status == "*":
                state["enabled"] = True
                state["sql_open"] = True
                state["active"] = True
            elif status == "#":
                state["enabled"] = False
            else:
                raise ValueError("status wrong?", status)
            state["siglev"] = int(info[1:])
            states.append(state)
        return states

    @property
    def voter_state(self):
        """
        returns the last complete(!) voter state as a dict, with an added timestamp field
        :return:
        """

        with open("state", "r") as state_file:
            state_raw = state_file.read()
            if len(state_raw) < 1:
                # no data at all yet
                return {}
            if state_raw[-1] != '\n':
                # last line isn't complete, take the one before
                state_raw = state_raw.splitlines()[-2]
            else:
                state_raw = state_raw.splitlines()[-1]
        timestamp, _, state_json = state_raw.split(' ', 2)
        try:
            state = json.loads(state_json)
        except Exception as e:
            try:
                state = self.parse_old_state(state_json)
            except Exception as e:
                self.log.error("failed parsing state with error: %s and data: %s", e, state_json)
                return {}
        result = {"time": datetime.fromtimestamp(float(timestamp))}
        for item in state:
            result[item["name"]] = item
        return result

    def wait_for_remote_state(self, name: str, state: str, expected: bool, timeout: int):
        """
        wait for a remote to have state set to expected, with a timeout
        :param state: ["active", "enabled", "sql_open"]
        :param name:
        :param expected:
        :param timeout:
        :return:
        """
        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            if self.voter_state.get(name, {}).get(state) == expected:
                return True
        return False

    @property
    def active_remote_by_tone(self):
        with open("audio", "r") as audio:
            # ts, freq = audio.read().split(" ", 1)
            try:
                freq = audio.readlines()[-2]  # take the second last, so we're sure it's complete
                self.log.debug("Tone: %s", freq)
            except IndexError:
                # self.log.warning("no audio data yet")
                return None
            return self.remote_tones.get(int(freq), None)

    def wait_for_remote_by_tone(self, name: str, timeout: int):
        """
        wait for a remote to be found by tone in the audio output
        :param name:
        :param timeout:
        :return:
        """
        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            if self.active_remote_by_tone == name:
                return True
        return False


def main():
    logging.basicConfig(level=logging.INFO)
    dc = Environment()
    dc.start()
    dc.open_squelch("remote1")
    dc.wait_for_remote_by_tone("remote1", 5)
    sleep(5)
    dc.stop()


if __name__ == "__main__":
    main()
