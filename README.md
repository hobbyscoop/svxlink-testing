This repo helps us testing svxlink to make sure our patches still work.

## Todo
* write tests
  * use [ts-fifo.sh](ts-fifo.sh) to write pty to file, to overcome docker boundary
  * what language to write tests in?
* GitHub actions

## Run
* build-image.sh
* docker-compose up -d
* `run tests`
