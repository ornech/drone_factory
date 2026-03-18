#!/bin/bash
export LD_LIBRARY_PATH="/data/projets/sim_drone/tools/flightgear/squashfs-root/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec /data/projets/sim_drone/tools/flightgear/squashfs-root/usr/bin/fgfs "$@"
