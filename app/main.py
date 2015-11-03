from google.appengine.api import urlfetch
from google.appengine.ext import ndb

import csv
import re
import os
from cStringIO import StringIO

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                                'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class LogfileSection(ndb.Model):
    data = ndb.BlobProperty()
    datadate = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def singleton(cls):
        return cls.get_or_insert('SINGLE')


class MainPage(webapp2.RequestHandler):

    def get(self):
        bks = LogfileSection.singleton()

        template_values = {'data_date': bks.datadate,
                           }
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


class ReloadLogfile(webapp2.RequestHandler):
    def get(self):
        data = urlfetch.fetch(
            'https://nethack.devnull.net/tournament/scores.xlogfile',
            deadline=60).content

        savescores(data)


class UniqueDeaths(webapp2.RequestHandler):
    def get(self, username):
        self.response.headers['Content-Type'] = 'text/plain'
        mydeaths = []
        possibledeaths = []
        done = set()

        with open('death_yes.txt') as deathyes:
            for line in deathyes:
                possibledeaths.append(re.compile(line.rstrip()+'$'))

        scores = readscores()
        reader = csv.reader(scores, delimiter=':')

        for line in reader:
            if username == line[15].split('=')[1]:
                mydeaths.append(line[16]
                                .split('=')[1].decode('unicode-escape'))

        for death in mydeaths:
            # the tournament seems to do this; if so it's a bug...
            death = death.replace('(with the Amulet)', '')
            for exp in possibledeaths:
                if exp.match(death.replace('\\', '').replace(' *', '')):
                    done.add(exp)

        self.response.write(str(len(done))+'\n')

        tmp = []
        for d in possibledeaths:
            if d not in done:
                tmp.append(d.pattern)

        for d in tmp:
            self.response.write(d + '\n')


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
    bks = LogfileSection.singleton()
    return StringIO(bks.data)


def savescores(data):
    """write scores back to datastore, from string"""
    bks = LogfileSection.singleton()
    bks.data = data
    bks.put()
