#!/usr/bin/env bash

wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install ./google-chrome-stable_current_amd64.deb
# wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
# dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install