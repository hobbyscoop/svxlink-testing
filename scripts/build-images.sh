#!/bin/bash
set -e
git clone https://github.com/hobbyscoop/svxlink.git || true
cd svxlink
branch=${1:-hobbyscoop}
echo "BUILDING FOR ${branch}"
git checkout "${branch}"
git pull

docker build --progress=plain -f ../Dockerfile -t "svxlink:${branch}" .
