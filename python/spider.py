# Copyright 2006 Kevin Dwyer

import urllib
from twisted.internet import gtk2reactor
gtk2reactor.install()
import twisted
import twisted.web.client as client
import urlparse
import Queue
import re
import time
import sys
import random
import gobject
from twisted.internet import reactor

#def getPage(url):
#    return urllib.urlopen(url).read()

AGENT = "crawler/0.1"

def getPage(url):
    return client.getPage(url, agent=AGENT)

urlRE = "<\s*a\s+[^>]*href\s*=\s*[\"']?([^\"' >]+)[\"]?.*?>(.*?)</a>"
def findLinks(page):
    return re.findall(urlRE, page)

def urlClean(url):
    return url.split("#")[0]


def resolveLinks(base, links):
    return [(urlClean(urlparse.urljoin(base, link[0])), link[1])
            for link in links]

LOGFILE = None
def log(msg):
    global LOGFILE
    LOGFILE.write("%s: %s\n" % (time.ctime(), msg))
    LOGFILE.flush()

visitedLinks = {}
active = {}
queue = Queue.Queue()
def parse(page, url):
    print "HIT:", url
    links = resolveLinks(url, findLinks(page))
    #print links
    visitedLinks[url] = True
    [queue.put(link) for link in links if link[0] not in visitedLinks and
     link[0] not in queue.queue]
    del active[url]

def handleErr(err, url):
    print "%s:%s" % (url, err)
    try:
        del active[url]
    except:
        print "D'oh!, we hit this twice?!: %s" % url

def mainloop():
    #visitedLinks = {}
    #queue.put((rootLink, "FIGHT"))
    print active
    if queue.qsize() and len(active) < 10:
        print "active:", len(active)
        url, linktext = queue.get()
        if url in visitedLinks:
            print "Found cycle:", url
            return True

        try:
            print "URL:%s -- '%s'" % (url, linktext)
            log("%s:'%s'" % (url, linktext))
            deferred = getPage(url)
            deferred.addCallback(parse, url)
            deferred.addErrback(handleErr, url)
            active[url] = deferred
        except Excpetion, e:
            print "Except:", e
            #time.sleep(5)

        #print "VL:", visitedLinks
        print "Q:", queue.qsize()
        #time.sleep(random.randint(8,15))

    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        rootLink = sys.argv[1]
    else:
        rootLink = "http://digg.com/"

    queue.put((rootLink, "FIGHT"))

    LOGFILE = file("travel.log", "w")

    try:
        #reactor.callWhenRunning(mainloop, rootLink)
        gobject.timeout_add(0.01 * 1000, mainloop)
        reactor.run()
    finally:
        LOGFILE.close()
