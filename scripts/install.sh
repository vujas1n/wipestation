#!/bin/bash
# installs system dependencies needed by wipestation

set -e  # exit on first error

echo "Updating package lists..."
sudo apt update

echo "Installing required tools..."
sudo apt install -y nwipe hdparm nvme-cli python3 python3-pip python3-venv

echo "Installing python dependencies..."
pip3 install -r requirements.txt

echo "Installing udev rule..."
sudo cp udev/99-wipestation.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Setup complete."