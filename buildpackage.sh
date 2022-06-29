#!/bin/bash

# build the debian package

platforms=( bionic focal jammy bullseye buster )

for platform in "${platforms[@]}"
do
  sed "s/%platform%/$platform/g" debian/changelog.template > debian/changelog
  dpkg-buildpackage -rfakeroot -tc -sa -us -uc -I".directory" -I".git" -I"buildpackage.sh"
  rm debian/changelog
done


#dpkg-buildpackage -rfakeroot -tc -sa -us -uc -I".directory" -I".git" -I"buildpackage.sh"
