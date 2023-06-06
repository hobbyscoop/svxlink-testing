#!/bin/bash
# reads from a fifo and for each line rewrite a file, and prefix the line with the timestamp
while true
do
  cat "$1" | tail -1 | sed -e "s/^/$(date +%s) /" >> "$2"
done &
