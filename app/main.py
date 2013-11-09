import webapp2

import csv
import re
import sys

class MainPage(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!')

class UniqueDeaths(webapp2.RequestHandler):
    def get(self, username):
        self.response.headers['Content-Type'] = 'text/plain'
        mydeaths = set()
        possibledeaths=set()
        done=set()

        with open('death_yes.txt') as deathyes:
            for line in deathyes:
                possibledeaths.add(re.compile(line.rstrip()+'$'))


        with open('scores.xlogfile') as scores:
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
    ], debug=True)
