# Copyright 2006-2008 Kevin Dwyer
from django.db import models

## class Feed(models.Model):
##     name = models.CharField(max_length=255, unique=True)
##     url = models.URLField(verify_exists=False, unique=True)

# Temporary
class Feed(object):
    def __init__(self, name, url, id):
        self.name = name
        self.url = url
        self.id = id
import db
def getFeeds():
    conn = db.getConnection()
    curs = conn.cursor()
    sql = "select name, url, feed_id from feeds"
    curs.execute(sql)
    return [Feed(row[0], row[1], row[2]) for row in curs.fetchall()]

## class Deal(models.Model):
##     feed = models.ForeignKey(Feed)
##     description = models.CharField(max_length=600)
##     url = models.URLField(verify_exists=False, unique=True)
##     received_on = models.DateTimeField()

class User(models.Model):
    name = models.CharField(max_length=20)
    email = models.CharField(max_length=200)
    password = models.CharField(max_length=32)

class Alert(models.Model):
    owner = models.ForeignKey(User)
    term = models.CharField(max_length=600)
    last_found = models.DateTimeField()
    total_hits = models.IntegerField()
    last_snooze = models.DateTimeField()
