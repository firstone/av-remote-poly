#!/usr/bin/env sh

pip3 install -r requirements.txt --user

if [ ! -f cfg/config.yaml ]; then
    cp cfg/config_sample.yaml cfg/config.yaml
fi
./polyprofile.py --config cfg/server_config.yaml --destination .

curl -L https://github.com/Calsign/APDE/raw/fdc22eb31048862e1484f4b6eca229accda61466/APDE/src/main/assets/aapt-binaries/aapt-arm-pie > aapt-arm-pie
