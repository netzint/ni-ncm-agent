#!/bin/bash

# build the debian package

dpkg-buildpackage -rfakeroot -tc -sa -us -uc -I".directory" -I".git" -I"buildpackage.sh"

mkdir archives
mv ../ni-ncm-agent_* ./archives

exit 0
