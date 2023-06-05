#!/bin/bash
docker exec remote1 /squelch.sh Z
docker exec remote2 /squelch.sh Z
docker exec svxlink /control.sh ENABLE RemoteRx1
docker exec svxlink /control.sh ENABLE RemoteRx2
