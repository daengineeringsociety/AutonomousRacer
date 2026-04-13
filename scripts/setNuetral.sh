#!/bin/bash

echo "Set CHASSIS POWER OFF"
sleep 5
sudo sh -c 'echo 1500000 > /sys/class/pwm/pwmchip0/pwm0/duty_cycle'
echo "NOW TURN ON CHASSIS POWER"
sleep 5
echo "You're good to go!"
