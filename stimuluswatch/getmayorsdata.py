#!/usr/bin/env python
#
# Copyright 2008 Kevin Dwyer

import sys
import lxml.html
import lxml.html.soupparser
import urllib2

if __name__ == '__main__':
    cityurl = 'http://www.usmayors.org/mainstreeteconomicrecovery/stimulussurveyparticipants.asp'
    doc = lxml.html.parse(cityurl)
    root = doc.getroot()

    cities = []
    for form in root.forms:
        city = state = None
        for child in form:
            if child.name == 'City':
                city = child.value.strip()
            elif child.name == 'State':
                state = child.value.strip()

        if (city and not state) or (not city and state):
            raise Exception('missing parts: %s, %s' % (city, state))
        if city and state:
            cities.append((city, state))

    cityurl = 'http://www.usmayors.org/mainstreeteconomicrecovery/stimulussurveyparticipantsdata.asp?City=%s&State=%s'
    for city, state in cities:
        print >> sys.stderr, "Working on:", city, state
        city = urllib2.quote(city)
        state = urllib2.quote(state)
        cityroot = None
        while cityroot is not None:
            try:
                cityroot = lxml.html.soupparser.parse(urllib2.urlopen(cityurl % (city, state))).getroot()
            except urllib2.URLError:
                print "error, retrying"
        
        table = cityroot.cssselect('table.pagesSectionBodyTight')[0]
        header = []
        row = []
        for td in table.cssselect('td'):
            if 'colspan' in td.keys():
                break

            value = td.text_content().strip()
            #print value
            if len(header) < 6:
                header.append(value)
            else:
                if len(row) == 6:
                    rowdata = dict(zip(header, row))
                    print rowdata
                    row = []

                row.append(value)

        rowdata = dict(zip(header, row))
        print rowdata

