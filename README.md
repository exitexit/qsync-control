# QSync Control

Like my code? [![donate](https://img.shields.io/badge/%24-Buy%20me%20a%20coffee-ef864e.svg)](https://www.buymeacoffee.com/exitexit) or consider donating to my Ether wallet: 0x3c2f57171FBc82D1F54de74f20Ce174ca4874298

A Python library for operating QMotion blinds controlled by a QSync device on the local network. The program is written in Python 3.
Network protocol dissection can be found in the comments within the [qsync_control.py](./qsync_control.py) file. Protocol details are inferred from Wireshark monitoring of the network traffic between the [QMotion QSync iPhone app](https://apps.apple.com/us/app/qmotion-qsync/id1269686306) and the [QSync device](http://www.qmotionshades.com/products/25-controls/218-qsync).

If you are looking for a Javascript library for the same purpose, check out https://github.com/devbobo/qmotion

## Content

##### qsync_control.py
The file contains a set of utilities for communicating with the QSync device and controlling the QMotion blinds paired with the QSync device. The code is written mostly in procedural format for ease of comprehension.

## Install PyPI Package
```
pip3 install qsync_control
```
More documentation can be found at: https://pypi.org/project/qsync-control/

## Sample Usage

First, identify the local IP address of the QSync device:
```
>>> import qsync_control
>>> qsync_control.discover_qsync()
QSYNC IP: 192.168.0.132
```
Then assign the obtained IP address to the `QSYNC_IP` property:
```
>>> qsync_control.QSYNC_IP = '192.168.0.132'
```
See a list of all the blind groups and scenes stored in the QSync device:
```
>>> qsync_control.retrieve_groups_and_scenes()
GROUPS: ['Living Room', 'Dining Room', 'Office', 'Bedroom']
SCENES: ['Movie Scene', 'Morning Scene', 'Night Scene']
```

Example: set a blind group to a specific shade position (fully up: 100, fully down: 0):
```
>>> qsync_control.set_group('Living Room', 100)
```
Example: set multiple blind groups to specific shade positions:
```
>>> qsync_control.set_groups('Living Room', 100, 'Bedroom', 0, 'Office', 0)
```
Example: set a scene:
```
>>> qsync_control.set_scene('Movie Scene')
```
