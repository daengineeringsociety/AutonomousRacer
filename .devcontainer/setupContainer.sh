#!/bin/bash

#This is run right after container is built
#Use this script to setup container repos adn environment
echo 'Installing Apt Reqs'
sudo apt update
xargs sudo apt install -y < apt-installs.txt #Any additional Apt reqs, put em here (wont be in the docker cache)
cd /workspaces/deepracer_project/
git submodule update --remote #Update all submodules with the latest commit - Ex. the iOS ArKit Repo
echo "'You are all good to go!'"