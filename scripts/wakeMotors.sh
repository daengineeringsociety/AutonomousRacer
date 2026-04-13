#!/bin/bash
echo "Waking up motor controllers..."
sudo systemctl start deepracer-core
sleep 5  # Give it time to pull the pins high
echo "Freeing PWM sysfs locks..."
# This gives read/write access to all I2C buses to every user
sudo systemctl stop deepracer-core
# This gives read/write access to all I2C buses to every user
sudo chmod 666 /dev/i2c-*
#PWM Chip
sudo chmod -R 777 /sys/class/pwm/pwmchip0/
echo "Hardware ready for Docker container!"

