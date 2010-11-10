#!/usr/bin/env python
#
# Copyright (C) 2006 Kevin Dwyer <kevin@pheared.net>
#
# Western Digital Button Daemon

import sys
import os

# Lacking any real documentation, I don't know what all of these characters
# mean.  Probably some indicators as to the type of command coming in, etc.
key_hdr = ['\xa6', '\x00', '\xa0', '\xff']
key_end = ['\x00', '\x00', '\x00', '\xa7', '\x00', '\xa0', '\xff', '\x00',
           '\x00', '\x00', '\x00']

def concat(charlist):
    return reduce(lambda x,y:x+y, charlist)

class Function(object):
    def __init__(self, name, keycode):
        self.name = name
        self.keycode = keycode

    def __hash__(self):
        return id(self.name + self.keycode)

    def __eq__(self, other):
        return self.keycode == other.keycode

key_up                 = Function('Up',
                                  concat(key_hdr + ['\x00'] + key_end))
key_clock              = Function('Clock',
                                  concat(key_hdr + ['\x01'] + key_end))
key_backup             = Function('Backup',
                                  concat(key_hdr + ['\x02'] + key_end))
key_clock_backup       = Function('Clock+Backup',
                                  concat(key_hdr + ['\x03'] + key_end))
key_power              = Function('Power',
                                  concat(key_hdr + ['\x04'] + key_end))
key_clock_power        = Function('Clock+Power',
                                  concat(key_hdr + ['\x05'] + key_end))
key_backup_power       = Function('Backup+Power',
                                  concat(key_hdr + ['\x06'] + key_end))
key_clock_backup_power = Function('Clock+Backup+Power',
                                  concat(key_hdr + ['\x07'] + key_end))

shutdown = Function('Shutdown', concat(key_hdr + ['\x08'] + key_end +\
                                       key_hdr + ['\x08'] + key_end +\
                                       key_hdr + ['\x04'] + key_end +\
                                       key_hdr + ['\x02'] + key_end))

fns = [key_up, key_clock, key_backup, key_clock_backup, key_power,
       key_clock_power, key_backup_power, key_clock_backup_power]
functions = dict(zip([fn.keycode for fn in fns], fns))

hid_device = '/dev/hiddev0'

class Action(object):
    def __init__(self, command):
        self.command = command

    def act(self):
        rv = os.system(self.command)
        if rv:
            raise Exception, 'command "%s" returned %i' % (self.command, rv)

    def response(self):
        #write(shutdown)
        pass

actions = {key_backup:[Action("kdesu 'rsync -ax --delete /home /media/WDbackup/ganon/'")], key_power:[Action('kidalog --msgbox "Shutdown.."')]}

def main():
    hiddev = file(hid_device)

    next_fn = None
    while True:
        cmd = []
        for i in range(16):
            cmd.append(hiddev.read(1))
        cmd = concat(cmd)

        try:
            fn = functions[cmd]
            print 'Got %s' % fn.name
            if fn.name != 'Up':
                next_fn = fn
        except KeyError:
            print "Got unknown keycode: %s" % cmd
            continue

        if fn.name == 'Up':
            if next_fn in actions:
                for action in actions[next_fn]:
                    action.act()
                    os.system('kdialog --msgbox "%s completed"' % next_fn.name)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        main()
    else:
        pid = os.fork()
        if pid == 0: # if pid is child
            os.setsid() # Start new process group.
            pid = os.fork()
            if pid == 0: # if pid is child
                main()
            else:
                print "pid:", pid
