# Copyright 2006-2008 Kevin Dwyer
#import psycopg
import db

class Deal(object):
    # I don't really want to use django's models for this because the dealbot
    # has to be able to talk to the database too.
    def __init__(self, deal_id=None, description=None, feed=None, url=None,
                 received_on=None):
        self.deal_id = deal_id
        self.description = description
        self.feed = feed
        self.url = url
        self.received_on = received_on

def getDeals(num=None, since=None, terms=None):
    """\
    @param num: Number of deals to return.  None means all.
    @param since: Return deals with a higher deal_id than since.
    @param terms: Search term string.

    @return: Generator that yields matching deals.
    """
    params = []

    conn = db.getConnection()
    curs = conn.cursor()

    # These fields are lined up to correspond with Deal.__init__
    sql = "select d.deal_id, d.description, f.name, d.url, d.received_on from deals d join feeds f on d.feed_id = f.feed_id "

    whereClause = []
    if since:
        # FIXME: This assumes deal_ids are chronological
        whereClause.append("deal_id > %s")
        params.append(since)

    if terms:
        terms = parse_terms(terms)
        whereClause.append('upper(d.description) like upper(%s)')
        params.append("'%" + '%'.join(terms) + "%'")

    if whereClause:
        sql += (' where ' + ' AND '.join(whereClause))

    sql += " order by d.received_on desc, d.deal_id desc"

    if num:
        sql += " limit %s"
        params.append(num)

    try:
        curs.execute(sql, params)
    except:
        conn.commit()
        raise

    next = 1
    while next:
        next = curs.fetchone()
        if next:
            yield Deal(*next)

    conn.commit()

def parse_terms(termstring):
    in_quote = False
    terms = []
    term = ""
    for c in termstring:
        if c not in (' ', '"') or (c == ' ' and in_quote):
            term += c
        if c == ' ' and not in_quote:
            terms.append(term)
            term = ""
        if c == '"' and in_quote:
            in_quote = False
            terms.append(term)
        if c == '"' and not in_quote:
            in_quote = True
    if term:
        terms.append(term)
    return terms

def getDealByID(deal_id):
    conn = db.getConnection()
    curs = conn.cursor()

    # These fields are lined up to correspond with Deal.__init__
    sql = "select d.deal_id, d.description, f.name, d.url, d.received_on from deals d join feeds f on d.feed_id = f.feed_id where d.deal_id=%s"

    params = [deal_id]

    try:
        curs.execute(sql, params)
    except:
        conn.commit()
        raise

    deal = None
    row = curs.fetchone()
    if row:
        deal = Deal(*row)

    conn.commit()
    return deal
