#!/usr/bin/python

import sys
import re
import datetime
import psycopg

try:
    conn = psycopg.connect("dbname=crime user=crime host=ganon password=XXXX")
except:
    print "Error connecting to database"
    raise

def stripHTML(s):
    news = []
    inTag = False
    for c in s:
        if c == "<":
            inTag = True
        elif c == ">":
            inTag = False
        else:
            if not inTag:
                news.append(c)

    return "".join(news)

def fixSpace(s):
    """
    Collapse whitespace in string s
    """
    return re.sub(r'(\S)\s+(\S)', r'\1 \2', s)

def fixAnd(s):
    """ Fix the various iterations of 'and' """
    a = " AND "
    news = s.replace("&", a)
    news = news.replace("W/", a)
    news = news.replace("/", a)
    return news

def makeDate(s):
    m,d,y = s.replace('/', '-').split('-')
    # Wee, not y2100 compliant
    return datetime.date(int(y)+2000, int(m), int(d))

def insert(curs, crime, date, location, details):
    # First determine the crime type ID or create a new one
    curs.execute("select type_id from crime_type where type_name=%s",
                 [crime])
    r = curs.fetchall()
    if len(r):
        typeId = r[0][0]
    else:
        curs.execute("insert into crime_type (type_name) values (%s)", [crime])
        curs.execute("select currval('crime_type_type_id_seq')")
        r = curs.fetchall()
        typeId = r[0][0]

    # Now get the location ID or create a new one
    curs.execute("select loc_id from crime_location where loc_desc=%s",
                 [location])

    r = curs.fetchall()
    if len(r):
        locId = r[0][0]
    else:
        curs.execute("insert into crime_location (loc_desc) values (%s)",
                     [location])
        curs.execute("select currval('crime_location_loc_id_seq')")
        r = curs.fetchall()
        locId = r[0][0]

    # Now insert the event
    curs.execute("insert into crime_event (event_type, event_location, " \
                 "event_date, event_desc) values (%i, %i, %s, %s)",
                 [typeId, locId, str(date), details])

if __name__ == "__main__":

    #data = file(sys.argv[1]).read()
    data = sys.stdin.read()
    sText = "HYATTSVILLE CITY POLICE CRIME REPORT"
    eText = '\n-----'

    start = data.find(sText)
    end = data.find(eText, start)

    body = data[start+len(sText):end].strip()

    # Remove the extra whitespace that sometimes shows up between newlines.
    body = re.sub(r'\n\s+\n', r'\n\n', body)
    #print `body`
    body = body.split('\n\n')

    title = body[0]

    print "Title: " + title

    curs = conn.cursor()
    for event in body[3:]:
        event = event.strip()

        if len(event) < 10:
            continue

        # Get the date
        try:
            ds, moreinfo = event.split('\t')
        except:
            print `event`

        try:
            date = makeDate(ds)
            print "Date of event: ", date
        except:
            if ds.find("Non-text portions of this message have been removed") == -1:
                break
            raise "Error: " + ds

        # Get the crime
        comma = moreinfo.find(',')
        # Is fixSpace still necessary?
        crime = fixSpace(fixAnd(moreinfo[:comma].strip().upper()))
        if crime == 'THEFT UNDER':
            crime = 'THEFT'
        print "Crime:         ", crime

        # Get the details
        ds = moreinfo[comma+1:].strip()

        colon = ds.find(':')
        comma = ds.find(',')

        # Clean up the details, removing new lines and html.
        ds = " ".join([l.strip() for l in ds.splitlines()])

        if colon == -1 and ds[0] not in "0123456789":
            # Weird case where there is no location
            location = ""
            details = ds
        elif colon < comma or comma == -1:
            location = ds[:colon]
            details = ds[colon+1:]
        else:
            location = ds[:comma]
            details = ds[comma+1:]

        details = details.strip()
        details = details.replace('\x92', "'")
        details = details.replace('\x93', '"')
        details = details.replace('\x94', '"')
        details = details.replace('\xe9', "e")
        details = details.replace("&#8217;", "'")

        print "Location:      ", `location`
        print "Details:       ", `details`
        #print unicode(details)

        insert(curs, crime, date, location, details)

        print

    #conn.rollback()
    conn.commit()
