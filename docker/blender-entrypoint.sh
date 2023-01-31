#!/bin/bash
set -e
USER_ID=${LOCAL_UID:-9001}
GROUP_ID=${LOCAL_GID:-9001}

# DEV Setting
service ssh restart

echo "Starting__ with UID: $USER_ID, GID: $GROUP_ID"
usermod -u $USER_ID mash
groupmod -g $GROUP_ID mash
export HOME=/home/mash
id mash
exec /usr/sbin/gosu mash /bin/bash