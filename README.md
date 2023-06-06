This repo helps us testing svxlink to make sure our patches still work.

## Todo
* write tests
  * use [ts-fifo.sh](ts-fifo.sh) to write pty to file, to overcome docker boundary
  * what language to write tests in?
  * see if we have enough I/O opportunities with the PTYs
  * see how we can take in echolink testing, as we have a patch for voter preference for that
* GitHub actions

## Run
* run the Github Action

## Test interfaces
### controlling the remoteRXs
```bash
docker exec remote1 /squelch.sh Z # close sql
docker exec remote1 /squelch.sh O # open sql
```

### controlling the voter
```bash
docker exec svxlink /control.sh ENABLE RemoteRx1 # enable rx1
docker exec svxlink /control.sh DISABLE RemoteRx1 # disable rx1
docker exec svxlink /control.sh MUTE RemoteRx1 # mute rx1
```

### reading the voter/repeater logic state
* `/dev/shm/state`
* document how to use with ts-fifo.sh

### reading the repeater TX state
* `/dev/shm/ptt`
* document how to use with ts-fifo.sh
* `T` is on, `R` is off

