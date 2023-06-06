#!/bin/bash
set -e
git clone https://github.com/hobbyscoop/svxlink.git || true
cd svxlink
git checkout hobbyscoop
git pull

docker build --progress=plain -f ../Dockerfile -t svxlink .
