#!/usr/bin/python

# Copyright (C) 2005 Kevin Dwyer

import sys, os, fnmatch
import stat, statvfs
import string
import getopt
import random
import shutil

def usage():
    print "sampler does what iTunes does for the iPod shuffle, only for my Rio"
    print "(or anything that can be mounted in Unix)"
    print
    print "-d specifies the source directory"
    print "-m specifies the mount point"

def main():
    random.seed()
    mountPoint = None
    sourceDir = None
    opts, args = getopt.getopt(sys.argv[1:], "d:hm:")

    for o, a in opts:
        if o == "-m":
            mountPoint = a
        elif o == "-d":
            sourceDir = a
        elif o == "-h":
            usage()
            sys.exit()

    if not mountPoint:
        print "Using /media/FORGE/Music for mount point."
        mountPoint = "/media/FORGE/Music"
    if not sourceDir:
        print "Using CWD for source."
        sourceDir = os.getcwd()

    # Find mp3s
    fList = []
    for root, dirs, files in os.walk(sourceDir):
        for f in files:
            if fnmatch.fnmatch(string.lower(f), "*.mp3"):
                fList.append(os.path.join(root, f))

    #print fList
    print "Found: %s" % len(fList)

    fList = [(f, os.stat(f)[stat.ST_SIZE]) for f in fList]
    #print fList

    # Determine space on destination device
    dest = os.statvfs(mountPoint)
    destTotalBytes = dest[statvfs.F_BLOCKS] * long(dest[statvfs.F_BSIZE])
    destFreeBytes = dest[statvfs.F_BAVAIL] * long(dest[statvfs.F_BSIZE])

    print "Destination device has %s MB" % (destTotalBytes / 1024 / 1024)

    # Make a random playlist that will fit the drive
    random.shuffle(fList)
    bytesSpent = 0
    freeBytes = 1024*1024*3  # Rio has some kind of overhead or something
    playList = []

    while True:
        try:
            f = fList.pop()
            if bytesSpent + f[1] < (destTotalBytes - freeBytes):
                playList.append(f)
                bytesSpent += f[1]
                #print "Added %s / %s" % (f[0], f[1])

        except IndexError:
            break

    print "Picked %s songs" % len(playList)
    print "Picked %s MB" % (sum([f[1] for f in playList]) / 1024 / 1024)

    print "Destroying old data"
    for f in os.listdir(mountPoint):
        f = os.path.join(mountPoint, f)
        #print "Remove " + f
        os.remove(f)

    print "Copying new files"
    prog = progressBar(0, len(playList), 77)
    print prog, "\r",
    for i, (f, s) in enumerate(playList):
        #print "Copying " + f + " to " + os.path.join(mountPoint, os.path.basename(f))
        shutil.copyfile(f, os.path.join(mountPoint, os.path.basename(f)))
        prog.updateAmount(i)
        print prog, "\r",

    print
    print "Done"

class progressBar:
        def __init__(self, minValue = 0, maxValue = 10, totalWidth=12):
                self.progBar = "[]"   # This holds the progress bar string
                self.min = minValue
                self.max = maxValue
                self.span = maxValue - minValue
                self.width = totalWidth
                self.amount = 0       # When amount == max, we are 100% done 
                self.updateAmount(0)  # Build progress bar string

        def updateAmount(self, newAmount = 0):
                if newAmount < self.min: newAmount = self.min
                if newAmount > self.max: newAmount = self.max
                self.amount = newAmount

                # Figure out the new percent done, round to an integer
                diffFromMin = float(self.amount - self.min)
                percentDone = (diffFromMin / float(self.span)) * 100.0
                percentDone = round(percentDone)
                percentDone = int(percentDone)

                # Figure out how many hash bars the percentage should be
                allFull = self.width - 2
                numHashes = (percentDone / 100.0) * allFull
                numHashes = int(round(numHashes))

                # build a progress bar with hashes and spaces
                self.progBar = "[" + '#'*numHashes + ' '*(allFull-numHashes) + "]"

                # figure out where to put the percentage, roughly centered
                percentPlace = (len(self.progBar) / 2) - len(str(percentDone))
                percentString = str(percentDone) + "%"

                # slice the percentage into the bar
                self.progBar = self.progBar[0:percentPlace] + percentString + self.progBar[percentPlace+len(percentString):]

        def __str__(self):
                return str(self.progBar)

if __name__ == "__main__":
    main()
