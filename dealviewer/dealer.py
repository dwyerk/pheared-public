#!/usr/bin/env python
# Copyright (C) 2006-2007 Kevin Dwyer <kevin@pheared.net>

import os
import sys
import traceback
import feedparser
import threading
import time
import re
import htmlentitydefs
import logging
import socket
try:
    import psycopg
except:
    print "Warning: Missing psycopg module!"

from sets import Set
from ircbot import SingleServerIRCBot
from irclib import nm_to_n, nm_to_h, irc_lower
from irclib import ServerConnectionError

MAX_IRC_DEALS = 15

feedparser.USER_AGENT = "dlfndr/1.0"

# Make sure that urlopen times out
socket.setdefaulttimeout(15)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='dealer.log',
                    filemode='a')

logger = logging.getLogger('')
logger.setLevel(logging.INFO)

#Setup an echo to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(name)-7s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

log = logging

def entity_lookup(match):
    entity = match.group(0)[1:-1]
    return htmlentitydefs.entitydefs.get(entity, match.group(0))

def convert_entities(text):
    return re.sub(r'&(\w+);', entity_lookup, text)

class Dealer(SingleServerIRCBot):
    def __init__(self, dbconn, feeds, channel, nickname, server, port=6667,
                 localaddress=""):
        SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname,
                                    reconnection_interval=15)
        self.channel = channel
        self.nickname = nickname
        self.localaddress = localaddress
        self.dbconn = dbconn
        self.outputQueue = OutputQueue(self)
        self.outputQueue.start()
        self.dealFinder = DealFinder(self.outputQueue, channel, feeds, dbconn)
        self.dealFinder.start()

    def _connect(self):
        """ Better connect.  It supports the localaddress param. """
        password = None

        # This is a bug in irclib.  When the ServerConnection is disconnected,
        # it is removed from the connections list, but nothing adds it back.
        if self.connection not in self.ircobj.connections:
            self.ircobj.connections.append(self.connection)

        if len(self.server_list[0]) > 2:
            password = self.server_list[0][2]
        try:
            log.debug("Trying to connect")
            self.connect(self.server_list[0][0],
                         self.server_list[0][1],
                         self._nickname,
                         password,
                         ircname=self._realname,
                         localaddress=self.localaddress)
            log.debug("Connect finished")
        except ServerConnectionError:
            pass

    def get_version(self):
        return 'Dealer by kevin@pheared.net'

    def join_chan(self):
        self.connection.join(self.channel)

    def in_chan(self):
        log.debug("Channels: %s" % self.channels)
        log.debug("Connections: %s" % self.ircobj.connections)
        if self.channel in self.channels:
            log.debug(" Users: %s" % self.channels[self.channel].users())
            return True
        return False

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_nicknameinuse(self, c, e):
        self.nickname = c.get_nickname() + "`"
        c.nick(self.nickname)

    def on_kick(self, c, e):
        nick = e.arguments()[0]
        channel = e.target()

        # auto-rejoin
        if nick == c.get_nickname():
            time.sleep(1)
            c.join(channel)

    def on_privmsg(self, c, e):
        fromNick = nm_to_n(e.source())

        self.do_something(c, e, e.arguments()[0], fromNick)

    def on_pubmsg(self, c, e):
        fromNick = nm_to_n(e.source())
        msg = e.arguments()[0]
        if msg.startswith("!"):
            self.do_something(c, e, msg.strip()[1:], fromNick)

    def on_dccchat(self, c, e):
        log.info('Incoming DCC CHAT')
        if len(e.arguments()) != 2:
            return
        args = e.arguments()[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def do_something(self, c, e, cmd, nick):
        opts = None
        try:
            cmd, opts = cmd.split(' ', 1)
        except ValueError:
            pass

        log.info("Received cmd %s from %s" % (cmd, nick))

        if cmd == "search" and self.dbconn:
            if opts is None:
                self.outputQueue.send(nick, "Please specify a search term")
                return

            rows = self.dealFinder.searchDB(opts)
            log.info("Found %s hits for %s" % (len(rows), opts))
            if len(rows) == 0:
                self.outputQueue.send(self.channel,
                                      "%s's search is too narrow." % nick)
            else:
                self.outputQueue.send(self.channel,
                                      "%s found %s deals matching '%s'" \
                                      % (nick, len(rows), opts))
            if len(rows) > MAX_IRC_DEALS:
                self.outputQueue.send(nick, "Results truncated to last %s" \
                                      % MAX_IRC_DEALS)
            for i,row in enumerate(rows):
                if i >= MAX_IRC_DEALS:
                    break
                deal = "%i. " % (i+1)
                deal += self.dealFinder.dealFmt % ("", row[0], row[1], row[2])
                deal += (" (added on %s)" % row[3])
                self.outputQueue.send(nick, deal)

        if cmd == "stats" and self.dbconn:
            self.outputQueue.send(self.channel, "Deal stats:")
            curs = self.dbconn.cursor()
            sql = "(select f.name, count(*) from deals d join feeds f on d.feed_id = f.feed_id group by f.name order by count) union all select 'TOTAL', count(*) from deals"
            curs.execute(sql)
            rows = []
            maxlen = 0
            for row in curs.fetchall():
                rows.append(row)
                if len(row[0]) > maxlen: maxlen = len(row[0])

            for row in rows:
                self.outputQueue.send(self.channel, "\x0F%*s | %s" % \
                                      (maxlen+1, row[0], row[1]))

        if cmd == "KillYourSelfNow!":
            if opts is None:
                self.kill()
            else:
                self.kill(opts)

    def kill(self, msg="Making adjustments, brb."):
        self.outputQueue.keepWorking = False
        self.dealFinder.keepWorking = False
        log.debug("joining queue")
        self.outputQueue.join()
        log.debug("joined queue")
        log.debug("joining finder")
        self.dealFinder.join()
        log.debug("joined finder")
        self.die(msg)

class OutputQueue(threading.Thread):
    def __init__(self, bot):
        threading.Thread.__init__(self)
        self.setDaemon(1)
        self.bot = bot
        self.event = threading.Event()
        self.queue = []
        self.keepWorking = True

    def run(self):
        while self.keepWorking:
            log.debug("keepWorking!")
            self.event.wait(5)
            if self.bot.connection.is_connected() and not self.bot.in_chan():
                log.debug("Not in my channel!")
                self.bot.join_chan()
            while self.queue and self.bot.connection.is_connected() \
                      and self.bot.in_chan():
                log.debug("queue len: %s" % len(self.queue))
                try:
                    q_msg = self.queue.pop(0)
                    msg = (q_msg[0], q_msg[1].encode('ascii', 'replace'))
                    try:
                        self.bot.connection.privmsg(*msg)
                    except ValueError:
                        # HACK!
                        log.error("Got valueerror! Saving message.")
                        self.queue.insert(0, q_msg)  # Put the message back
                        self.bot.connection.connected = 0
                        log.error("Jumping server")
                        self.bot.jump_server()
                except UnicodeError, e:
                    log.exception('Got that unicode error')
                    f = file("badmsg.txt", "w")
                    f.write("Exception (%s) trying to send:" % e.args)
                    try:
                        f.write(msg[1])
                    except:
                        pass
                    f.write("\n")
                    f.close()
                except Exception:
                    log.exception('Exception getting msg/sending privmsg')


                time.sleep(2)
            self.event.clear()

    def send(self, target, msg):
        self.queue.append((target, msg.strip()))
        self.event.set()


class DealFinder(threading.Thread):
    def __init__(self, outputQueue, target, feeds, connection):
        threading.Thread.__init__(self)
        self.outputQueue = outputQueue
        self.target = target
        self.feeds = feeds
        self.dealFmt = "%s\x02[%s]\x02 %s (%s)"
        self.keepWorking = True
        #self.checkFrequency = 120
        self.checkFrequency = 600
        self.connection = connection
        if connection: self.cursor = connection.cursor()
        else: self.cursor = None

    def run(self):
        lastChecked = 0
        while self.keepWorking:
            time.sleep(5)
            now = time.time()
            if now - lastChecked < self.checkFrequency:
                continue
            lastChecked = now

            # Find some new items
            try:
                log.debug('Looking for new items')
                newDeals = self.findDeals()
                log.info("New items: %i" % len(newDeals))
            except Exception:
                log.exception("Error finding new items")

            # Save them for posterity (and searching)
            try:
                newDeals = self.saveDeals(newDeals)
            except Exception:
                log.exception('Error saving new items')

            # and send them to the output queue
            for deal in newDeals:
                try:
                    color = ""
                    if "Free" in deal.feed.name:
                        color = "\x034"
                    self.outputQueue.send(
                        self.target,
                        self.dealFmt % (color, deal.feed.name,
                                        convert_entities(deal.description),
                                        deal.url))
                except Exception:
                    log.exception('Error sending: %s' % `deal`)

    def findDeals(self):
        newDeals = []
        for feed in self.feeds:
            try:
                log.debug('Pinging %s', feed.name)
                newDeals.extend([Deal(feed, deal[0], deal[1]) for deal in feed.ping()])
                log.debug('Pong from %s (%i deals)', feed.name,
                          feed.last_ping_size)
            except Exception:
                log.exception('Exception while trying to ping %s' % feed.name)

        return newDeals

    def saveDeals(self, deals):
        if not self.connection:
            return deals

        keepers = []
        insert_sql = "insert into deals (feed_id, description, url, received_on) values (%s, %s, %s, %s)"
        update_sql = "update deals set description = %s, received_on = %s where url = %s"
        check_sql = "select deal_id from deals where url = %s"
        for deal in deals:
            try:
                self.cursor.execute(check_sql, (deal.url,))
                if self.cursor.rowcount:
                    params = (deal.description,
                              time.strftime('%Y%m%d %H:%M:%S'), deal.url)
                    self.cursor.execute(update_sql, params)
                    self.connection.commit()
                    #keepers.append(deal)
                else:
                    params = (deal.feed.id, deal.description, deal.url,
                              time.strftime('%Y%m%d %H:%M:%S'))
                    self.cursor.execute(insert_sql, params)
                    self.connection.commit()
                    keepers.append(deal)
            except psycopg.IntegrityError, e:
                if "unique_url" in e.args[0]:
                    log.warn('Somehow tried to add a dupe: %s' % deal.url)
                    self.connection.rollback()
                else:
                    raise
            except:
                log.exception('Exception saving deals')
                raise

        log.debug('Saved %i deals', len(keepers))
        return keepers

    def searchDB(self, searchterm):
        if not self.connection:
            return None

        curs = self.connection.cursor()
        try:
            curs.execute(
                "select f.name, d.description, d.url, d.received_on " \
                "from deals d join feeds f on f.feed_id = d.feed_id " \
                "where upper(d.description) like %s " \
                "order by d.received_on desc",
                ('%' + searchterm.upper() + '%',))
            return curs.fetchall()
        except psycopg.ProgrammingError:
            log.exception('Searching error')
            self.connection.rollback()
            return []

class Deal(object):
    def __init__(self, feed, description, url):
        self.feed = feed
        self.description = description.encode('ascii', 'replace')
        self.url = url.encode('ascii', 'replace')

    # Hmm, these are busted
    def __hash__(self):
        return hash((self.feed.id, self.description, self.url))

    def __eq__(self, other):
        return self.feed.id == other.feed.id \
               and self.description == other.description \
               and self.url == other.url

class Feed(object):
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.id = None
        self.last_ping_size = 0
        self._lastEntries = Set()
        self.ping()

    def ping(self):
        log.debug("Starting parse of %s", self.url)
        doc = feedparser.parse(self.url)
        log.debug("Finished parsing")
        current = Set([(entry.title, entry.link) for entry in doc.entries])
        #current = Set([Deal(self, entry.title, entry.link) for entry in doc.entries])
        log.debug("Created current deal set")
        new = current - self._lastEntries
        self._lastEntries = current
        self.last_ping_size = len(new)
        return new

def main():
    if len(sys.argv) > 1:
        configFile = sys.argv[1]
    else:
        configFile = 'dealer.config'

    try:
        config = eval(file(configFile).read())
    except IOError, e:
        if e.errno == 2:
            log.error("Missing config file.")
            sys.exit(1)
        raise

    conn = None
    feeds = [Feed(*feed) for feed in config['feeds']]
    if config['save_to_db']:
        dsn = "user=%(db_user)s dbname=%(db_name)s host=%(db_host)s " \
              "password=%(db_password)s" % config
        conn = psycopg.connect(dsn)

        curs = conn.cursor()

        fields = ['name', 'url']
        curs.execute("select %s from feeds" % ','.join(fields))
        dbFeeds = curs.fetchall()
        dbFeedNames = [f[0] for f in dbFeeds]
        dbFeedUrls = [f[1] for f in dbFeeds]

        for feed in feeds:
            if feed.url not in dbFeedUrls:
                log.warn("Missing feed %s, adding" % feed.name)
                curs.execute("insert into feeds (name, url) values ('%s', '%s')" \
                             % (feed.name, feed.url))

            curs.execute("select feed_id from feeds where url='%s'" \
                         % feed.url)
            feed.id = curs.fetchall()[0][0]
        conn.commit()

    bot = Dealer(conn, feeds, config['channel'], config['nick'],
                 config['server'], config['port'],
                 config.get('localaddress',''))
    #[bot.outputQueue.send(config['channel'], "Dealer online %i" % i) for i in range(10)]
    try:
        bot.start()
    except KeyboardInterrupt:
        log.warn('Received KeyboardInterrupt, killing...')
        bot.kill()

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        log.exception("Exception down in main.  Whoops!")
        raise
