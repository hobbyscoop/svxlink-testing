from datetime import datetime
import docker
import json
import logging
from subprocess import check_output
from time import sleep
logging.basicConfig(level=logging.INFO)


class Environment:
    def __init__(self):
        self.log = logging.getLogger(__class__.__name__)
        self.client = docker.from_env()

    def start(self):
        self.log.info("starting instances")
        if self.running > 0:
            self.log.warning("instances already running, stopping them first")
            self.stop()
        self.log.debug("running docker-compose up -d")
        check_output(["docker-compose", "up", "-d"])
        while self.running != 3:
            self.log.debug("waiting for containers to start...")
            sleep(1)
        self.start_pty_forwarder("state")
        self.start_pty_forwarder("ptt")
        self.reset()

    @property
    def running(self):
        return sum([c[1].status == "running" for c in self.containers.items()])

    def stop(self):
        self.log.info("stopping instances")
        check_output(["docker-compose", "down"])

    @property
    def containers(self):
        containers = self.client.containers.list()
        result = dict()
        for container in containers:
            result[container.name] = container
        return result

    def start_pty_forwarder(self, name):
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
        self.containers["svxlink"].exec_run("/bin/bash -c \"echo ENABLE {name} > /dev/shm/voter\"".format(name=name))

    def mute_remote(self, name):
        self.log.info("muting {}".format(name))
        self.containers["svxlink"].exec_run("/bin/bash -c \"echo MUTE {name} > /dev/shm/voter\"".format(name=name))

    def disable_remote(self, name):
        self.log.info("disabling {}".format(name))
        self.containers["svxlink"].exec_run("/bin/bash -c \"echo DISABLE {name} > /dev/shm/voter\"".format(name=name))

    def reset(self):
        self.log.info("resetting test env")
        self.open_squelch("remote1", False)
        self.open_squelch("remote2", False)
        self.enable_remote("remote1")
        self.enable_remote("remote2")

    @property
    def ptt_state(self):
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
        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            if self.ptt_state == state:
                return True
        return False

    @property
    def voter_state(self):
        with open("state", "r") as state_file:
            state_raw = state_file.read()
            if state_raw[-1] != '\n':
                # last line isn't complete, take the one before
                state_raw = state_raw.splitlines()[-2]
            else:
                state_raw = state_raw.splitlines()[-1]
        timestamp, _, state_json = state_raw.split(' ', 2)
        try:
            state = json.loads(state_json)
        except Exception as e:
            self.log.error("failed parsing state as json with error: %s and json: %s", e, state_json)
            return {}
        result = {"time": datetime.fromtimestamp(float(timestamp))}
        for item in state:
            result[item["name"]] = item
        return result

    def wait_for_remote_active(self, name: str, state: bool, timeout: int):
        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            if self.voter_state.get(name, {}).get("active") == state:
                return True
        return False


def main():
    dc = Environment()
    dc.start()
    print(dc.ptt_state)
    dc.open_squelch("remote1")
    print(dc.ptt_state)
    print(dc.voter_state)
    # sleep(5)
    dc.stop()


if __name__ == "__main__":
    main()