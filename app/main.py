import webapp2
from google.appengine.api import files
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext import blobstore

import csv
import re
import sys

class Logfile(ndb.Model):
    bk = ndb.BlobKeyProperty()
    datadate = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def singleton(cls):
        return cls.get_or_insert('SINGLE')
    

class MainPage(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!')

class ReloadLogfile(webapp2.RequestHandler):
    def get(self):
        data = urlfetch.fetch('https://nethack.devnull.net/tournament/scores.xlogfile', deadline=60).content
        file_name = files.blobstore.create(mime_type='text/plain')
        with files.open(file_name, 'a') as xlf:
            xlf.write(data)
        files.finalize(file_name)
        blob_key = files.blobstore.get_blob_key(file_name)
        bks = Logfile.singleton()
        oldbk = bks.bk
        bks.bk = blob_key
        bks.put()
        if oldbk:
            blobstore.delete(oldbk)
        

class UniqueDeaths(webapp2.RequestHandler):
    def get(self, username):
        self.response.headers['Content-Type'] = 'text/plain'
        mydeaths = set()
        possibledeaths=set()
        done=set()


        with open('death_yes.txt') as deathyes:
            for line in deathyes:
                possibledeaths.add(re.compile(line.rstrip()+'$'))

        bks = Logfile.singleton()
        scores = blobstore.BlobReader(bks.bk)
        reader = csv.reader(scores, delimiter=':')

        for line in reader:
            if username == line[15].split('=')[1]:
                mydeaths.add(line[16].split('=')[1].decode('unicode-escape'))


        for death in mydeaths:
            death = death.replace('(with the Amulet)', '') # the tournament seems to do this; if so it's a bug...
            for exp in possibledeaths:
                if exp.match(death):
                    done.add(exp)
                    
        self.response.write(str(len(done))+'\n')

        tmp = []
        for d in possibledeaths - done:
            tmp.append(d.pattern)

        for d in sorted(tmp):
            self.response.write(d + '\n')


application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        (r'/unique/(.*)', UniqueDeaths),
        (r'/reload', ReloadLogfile),
    ], debug=True)
