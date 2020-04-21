#!/usr/bin/env python3
#
# Copyright 2020 Tao Xie
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import socket

QSYNC_IP = '127.0.0.1'  # replace with the QSync IP address found by the discover_qsync() function
QSYNC_PORT = 9760  # QSync by default listens on TCP port 9760
DEBUG = 0

def discover_qsync():

    message = bytes(1)  # 1 byte of 0x00
    address = ('255.255.255.255', 9720)  # QSync by default listens on UDP port 9720

    socket_udp = None
    try:
        socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_udp.settimeout(1)  # timeout 1 sec
        socket_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # allow UDP broadcast

        socket_udp.sendto(message, address)
        (_data, (ip, _port)) = socket_udp.recvfrom(1024)
        print('QSYNC IP: ' + ip)

    except Exception as err:
        print('ERROR: ' + str(err))

    finally:
        if socket_udp is not None:
            socket_udp.close()


def retrieve_groups_and_scenes():
    socket_tcp = None
    try:
        socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_tcp.connect((QSYNC_IP, QSYNC_PORT))

        (groups, scenes) = retrieve_groups_and_scenes_with_socket(socket_tcp)
        print('GROUPS: ' + str(list(groups.keys())))
        print('SCENES: ' + str(list(scenes.keys())))

    except Exception as err:
        print('ERROR: ' + str(err))
        return None

    finally:
        if socket_tcp is not None:
            socket_tcp.close()

# Example:     1604000c000d  # full message of the initial QSync response specifying blind group count and scene count
# Flag:        16..........  # messages from QSync start with 0x16, messages to QSync start with 0x1b
# Body Length: ..04........  # indicating the message body is 4 bytes long
# Body:        ....000c000d  # body binaries with the specified length
# Body:        ....000c....  # number of blind groups in subsequent messages, in this case, 12 groups
# Body:        ........000d  # number of scenes in subsequent messages, in this case, 15 scenes

# Example:     162c010b000000000000000004a30011c65b08c79b00000180024c6976696e6720526f6f6d000000000000000000  # full message of a blind group description
# Flag:        16..........................................................................................  # messages from QSync start with 0x16
# Body Length: ..2c........................................................................................  # indicating the message body is 44 bytes long
# Body:        ......0b....................................................................................  # blind group code, for identifying this blind group when communicating with QSync
# Body:        ................................................8002........................................  # blind group address, for identifying this blind group in a particular scene
# Body:        ....................................................4c6976696e6720526f6f6d000000000000000000  # ASCII spelling out the group name, in this case, "Living Room"

# Example:     163b02800202c005020000000000000000000000000000000000000004a30011c65e9b5d41000000084d6f766965205363656e65000000000000000000  # full message of a scene description
# Flag:        16........................................................................................................................  # messages from QSync start with 0x16
# Body Length: ..3b......................................................................................................................  # indicating the message body is 59 bytes long
# Body:        ......800202c00502000000000000000000000000000000000000....................................................................  # 24 bytes of info, encoding up to 8 blind groups added to this scene
# Body:        ......8002................................................................................................................  # 1st group in this scene, with group address 0x8002
# Body:        ..........02..............................................................................................................  # 1st group's desired shade position, in this case, all the way down
# Body:        ............c005..........................................................................................................  # 2nd group in this scene, with group address 0xc005
# Body:        ................02........................................................................................................  # 2nd group's desired shade position, in this case, all the way down
# Body:        ..................................................................................4d6f766965205363656e65000000000000000000  # ASCII spelling out the scene name, in this case, "Movie Scene"

def retrieve_groups_and_scenes_with_socket(socket_tcp):
    if socket_tcp is None:
        raise ValueError('Socket cannot be null!')

    groups = {}
    scenes = {}

    socket_tcp.send(bytes.fromhex('1600'))
    debug_print('SEND: ' + '1600')
    data = socket_tcp.recv(2048)
    data_hex = bytes_to_hex(data)
    debug_print('RECV: ' + data_hex)

    head_hex = data_hex[:4]
    body_hex = data_hex[4:]

    # Parse group count and scene count.
    # Example: '1604000c000d' (12 groups and 15 scenes)
    if head_hex != '1604':
        print('ERROR: Invalid response!')
        return None
    group_count = int(body_hex[2:4], 16)
    scene_count = int(body_hex[6:8], 16)

    # Parse groups and scenes. QSync does not seem to send groups and scenes in any particular order.
    for i in range(group_count + scene_count):
        data = socket_tcp.recv(2048)
        data_hex = bytes_to_hex(data)
        debug_print('RECV: ' + data_hex)

        head_hex = data_hex[:4]
        body_hex = data_hex[4:]

        # Parse message describing a group.
        # Example: '162c010b000000000000000004a30011c65b08c79b00000180024c6976696e6720526f6f6d000000000000000000' ("Living Room")
        if head_hex == '162c':
            group_name_hex = body_hex[48:]
            group_name = bytes.fromhex(group_name_hex).decode().rstrip('\x00')
            group_addr = body_hex[44:48]
            group_code = body_hex[2:4]
            groups[group_name] = (group_addr, group_code)

            debug_print('GROUP: ' + group_name + '; ADDR: ' + group_addr + '; CODE: ' + group_code)

        # Parse message describing a scene.
        # Example: '163b02800202c005020000000000000000000000000000000000000004a30011c65e9b5d41000000084d6f766965205363656e65000000000000000000' ("Movie Scene")
        elif head_hex == '163b':
            scene_name_hex = body_hex[78:]
            scene_name = bytes.fromhex(scene_name_hex).decode().rstrip('\x00')

            # The first 24 bytes of the message body is an encoding of up to 8 groups added in this scene,
            # each group is specified with 3 bytes, encoding the group address (2 bytes) and the desired position code (1 byte).
            # Example: '800202c00502000000000000000000000000000000000000' (2 groups were added to this scene)
            settings_data = body_hex[2:50]
            settings_list = []
            for i in range(0, len(settings_data), 6):  # splitting the string into 6 hex digit chunks
                chunk = settings_data[i:i+6]
                if chunk == '000000':
                    break
                group_addr = chunk[:4]
                position_code = chunk[4:]
                settings_list.append((group_addr, position_code))
            scenes[scene_name] = settings_list

            debug_print('SCENE: ' + scene_name + '; ' + str(settings_list))

        else:
            print('ERROR: Invalid data!')
            return None


    return (groups, scenes)


# Example:     1b050000000901  # full message of the request sent to QSync to set a blind group to a specified shade position
# Flag:        1b............  # messages to QSync start with 0x1b
# Body Length: ..05..........  # indicating the message body is 5 bytes long
# Body:        ..........09..  # group code of the blind group to the controlled
# Body:        ............01  # desired shade position

# Fully open: 100
# Fully closed: 0
def set_group(arg_group_name, arg_position):
    position_code = position_to_code(arg_position)
    if position_code == '00':
        print('ERROR: Invalid position value!')
        return

    socket_tcp = None
    try:
        socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_tcp.connect((QSYNC_IP, QSYNC_PORT))

        (groups, _scenes) = retrieve_groups_and_scenes_with_socket(socket_tcp)

        if groups is not None and arg_group_name in groups:
            (_group_addr, group_code) = groups[arg_group_name]
            command_body = '000000' + group_code + position_code
            command_body_length = int(len(command_body)/2)  # number of bytes
            command = '1b' + num_to_hex(command_body_length) + command_body  # Example: '1b050000000901'

            socket_tcp.send(bytes.fromhex(command))
            debug_print('SEND: ' + command)

            data = socket_tcp.recv(2048)
            data_hex = bytes_to_hex(data)
            debug_print('RECV: ' + data_hex)

        else:
            print('ERROR: Group not found!')

    except Exception as err:
        print('ERROR: ' + str(err))

    finally:
        if socket_tcp is not None:
            socket_tcp.close()

# Example:     1b0a0000000b020000001602  # full message of the request sent to QSync to execute a scene
# Flag:        1b......................  # messages to QSync start with 0x1b
# Body Length: ..0a....................  # indicating the message body is 10 bytes long
# Body:        ....0000000b020000001602  # body encoding the blind groups and their desired positions defined in this scene
# Body:        ..........0b............  # 1st group in this scene, in this case, with group code 0x0b
# Body:        ............02..........  # 1st group's desired shade position, in this case, all the way down
# Body:        ....................16..  # 2nd group in this scene, in this case, with group code 0x16
# Body:        ......................02  # 2nd group's desired shade position, in this case, all the way down

def set_scene(arg_scene_name):
    socket_tcp = None
    try:
        socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_tcp.connect((QSYNC_IP, QSYNC_PORT))

        (groups, scenes) = retrieve_groups_and_scenes_with_socket(socket_tcp)

        if scenes is not None and arg_scene_name in scenes:
            addr_to_code = {}
            for group_addr, group_code in groups.values():
                addr_to_code[group_addr] = group_code

            settings_list = scenes[arg_scene_name]
            command_body = ''
            for group_addr, position_code in settings_list:
                group_code = addr_to_code[group_addr]
                command_body += '000000' + group_code + position_code

            command_body_length = int(len(command_body)/2)  # number of bytes
            command = '1b' + num_to_hex(command_body_length) + command_body  # Example: '1b0a0000000b020000001602'

            socket_tcp.send(bytes.fromhex(command))
            debug_print('SEND: ' + command)

            data = socket_tcp.recv(2048)
            data_hex = bytes_to_hex(data)
            debug_print('RECV: ' + data_hex)

        else:
            print('ERROR: Scene not found!')

    except Exception as err:
        print('ERROR: ' + str(err))

    finally:
        if socket_tcp is not None:
            socket_tcp.close()


# We can use the scene logic to set multiple blind groups in one request by
# constructing a virtual scene on the fly.
# Usage: set_groups(room1, pos1, room2, pos2, ...)
# Example: set_groups('Living Room', 100, 'Bedroom', 0)
def set_groups(*argv):
    argv_len = len(argv)
    if argv_len == 0:
        print('ERROR: Empty argument list!')
        return
    elif argv_len % 2 != 0:
        print('ERROR: Must have even number of arguments!')
        return
    else:
        custom_group_list = {}
        for i in range(0, argv_len, 2):
            group_name = argv[i]
            position_code = position_to_code(argv[i+1])
            if group_name is None:
                print('ERROR: Invalid group name!')
                return
            if group_name in custom_group_list:
                print('ERROR: Duplicate group name!')
                return
            if position_code == '00':
                print('ERROR: Invalid position value!')
                return
            custom_group_list[group_name] = position_code

    socket_tcp = None
    try:
        socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_tcp.connect((QSYNC_IP, QSYNC_PORT))

        (groups, _scenes) = retrieve_groups_and_scenes_with_socket(socket_tcp)

        # Construct a virtual scene with a custom list of blind groups.
        command_body = ''
        for group_name, position_code in custom_group_list.items():
            if groups is not None and group_name in groups:
                (_group_addr, group_code) = groups[group_name]
                command_body += '000000' + group_code + position_code
            else:
                print('ERROR: Group not found!')
                return

        command_body_length = int(len(command_body)/2)  # number of bytes
        command = '1b' + num_to_hex(command_body_length) + command_body  # Example: '1b0a0000000b020000001602'

        socket_tcp.send(bytes.fromhex(command))
        debug_print('SEND: ' + command)

        data = socket_tcp.recv(2048)
        data_hex = bytes_to_hex(data)
        debug_print('RECV: ' + data_hex)

    except Exception as err:
        print('ERROR: ' + str(err))

    finally:
        if socket_tcp is not None:
            socket_tcp.close()


# Range from 0 to 255
def num_to_hex(num):
    return '{:02x}'.format(num)

def bytes_to_hex(bytes):
    return ''.join('{:02x}'.format(x) for x in bytes)


# Fully open: 100
# Fully closed: 0
def position_to_code(position):
    if position == 0:
        return '02'
    if position == 12.5:
        return '0e'
    if position == 25:
        return '0c'
    if position == 37.5:
        return '0b'
    if position == 50:
        return '08'
    if position == 62.5:
        return '09'
    if position == 75:
        return '07'
    if position == 87.5:
        return '06'
    if position == 100:
        return '01'

    return '00'


def debug_print(message):
    if DEBUG:
        print(message)
