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
