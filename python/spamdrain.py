#!/usr/bin/python
#
# spamdrain -- a script that purges old e-mail in spam boxes
#              given a maximum age and a threshold
#
# purgeimap was written By Justin R. Miller <justin@solidlinux.com>
# purgeimap was then hacked to bits by Kevin Dwyer <kevin@pheared.net>
#

import os, string, time, imaplib, sys

if __name__ == "__main__":
    server = "mail.pheared.net"
    port = 993
    username = "xxxxxxxx"
    password = "xxxxxxxx"
    directory = "pheared.net/"
    folderMask = "*/spam"
    age = 7  # days
    purgeAmount = 30  # Only expunge a box if > purgeAmount

    timestamp = time.localtime(time.time() - (age * 86400))
    purgedate = time.strftime('%d-%b-%Y', timestamp)
    print "Destroying spam older than %s at threshold %i" % (purgedate,
                                                             purgeAmount)

    m = imaplib.IMAP4_SSL(server, port)
    m.login(username, password)

    spamboxesResp = m.list(directory, folderMask)
    spamboxes = map(lambda x:x.split()[3], spamboxesResp[1])
    #print spamboxes

    total = 0
    totalOld = 0
    totalExp = 0

    for box in spamboxes:
        print "Selecting %s..." % box,
        numMsgs = m.select(box)
        numMsgs = int(numMsgs[1][0])
        print "%i messages." % numMsgs,
        typ, msgs = m.search(None, '(BEFORE ' + purgedate + ')')

        if numMsgs < purgeAmount:
            print "Skipping."
            continue

        for num in string.split(msgs[0]):
            m.store(num, '+FLAGS', '(\Deleted)')

        #print typ, msgs
        totalOld += len(msgs[0].split())
        total += numMsgs
        expunged = m.expunge()
        if expunged[1] != [None]:
            print "Expunged %s messages." % len(expunged[1])
            totalExp += len(expunged[1])
        else:
            print

    m.logout()

    if total > 0:
        print "%i/%i (%.2f%%) spams over %i days old." \
              % (totalOld, total, (totalOld*100.0)/total, age)
    if totalOld > 0:
        print "%i/%i (%.2f%%) spams expunged." % (totalExp, totalOld,
                                                  (totalExp*100.0)/totalOld)
