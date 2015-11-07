"""devnull nethack tournament unique deaths"""
from google.appengine.api import urlfetch
from google.appengine.ext import ndb

import csv
import re
import os
from cStringIO import StringIO
import logging

import webapp2
import jinja2

BLOCK_SIZE = 1024 * 400


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                                'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class LogMetadata(ndb.Model):
    datadate = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def singleton(cls):
        return cls.get_or_insert('SINGLE')
    


class LogfileSection(ndb.Model):
    data = ndb.BlobProperty()
    datadate = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def singleton(cls):
        return cls.get_or_insert('SINGLE')


class MainPage(webapp2.RequestHandler):
    def get(self):
        bks = LogMetadata.singleton()

        template_values = {'data_date': bks.datadate,
                           }
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


class ReloadLogfile(webapp2.RequestHandler):
    def get(self):
        data = urlfetch.fetch(
            'https://nethack.devnull.net/tournament/scores.xlogfile',
            deadline=120).content

        savescores(data)


class UniqueDeaths(webapp2.RequestHandler):
    def get(self, username):
        mydeaths = []
        possibledeaths = []
        done = set()

        with open('death_yes.txt') as deathyes:
            for line in deathyes:
                possibledeaths.append(re.compile(line.rstrip()+'$'))

        scores = readscores()
        reader = csv.reader(scores, delimiter=':')

        for i, line in enumerate(reader):
            try:
                if username == line[15].split('=')[1]:
                    mydeaths.append(line[16]
                                    .split('=')[1].decode('unicode-escape'))
            except IndexError:
                logging.error("failed for line %s [%s]", i, line)
                raise
        posstmp = possibledeaths[:]

        for death in mydeaths:
            # the tournament seems to do this; if so it's a bug...
            #death = death.replace('(with the Amulet)', '')
            for i, exp in enumerate(possibledeaths):
                if exp and exp.search(death.replace('\\', '').replace(' *', '')):
                    done.add(exp)
                    possibledeaths[i] = None
                    break

        deaths = []
        for d in posstmp:
            if d not in done:
                deaths.append(('red', d.pattern))
            else:
                deaths.append(('green', d.pattern))
        template_values = {'deaths': deaths,
                           'count': len(done),
                           'player': username,
                           }
        template = JINJA_ENVIRONMENT.get_template('deaths.html')
        self.response.write(template.render(template_values))


class UniqueRedir(webapp2.RequestHandler):
    def post(self):
        un = self.request.get('username')
        if un is not None:
            self.redirect("/unique/" + self.request.get('username'))
        else:
            self.redirect("/")


application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        (r'/unique/(.*)', UniqueDeaths),
        (r'/unique', UniqueRedir),
        (r'/reload', ReloadLogfile),
    ], debug=True)


def readscores():
    """read scores from datastore, return filelike suitable for CSV reader"""
    bks = LogfileSection.query().fetch(200)
    data = ''.join(chunk.data for chunk in bks)
    return StringIO(data)


def savescores(data):
    """write scores back to datastore, from string"""
    logging.debug("Saving scores with data of length %s", len(data))
    md = LogMetadata.singleton()
    md.put_async()

    for ind, offset in enumerate(range(0, len(data), BLOCK_SIZE)):
        block = data[offset:offset + BLOCK_SIZE]
        key = "BLOCK-%03d" % ind
        logging.debug("made %s with length %s", key, len(block))
    
        bks = LogfileSection.get_or_insert(key)
        bks.data = block
        bks.put()
