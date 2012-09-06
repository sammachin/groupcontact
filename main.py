#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import webapp2
from twilio.rest import TwilioRestClient
import creds
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import mail
import os
from google.appengine.ext.webapp import template
import sys
import string
import unicodedata, re
import urllib
import random
import gspread



def makecode(group):
	seed = str(random.randrange(100000, 999999, 1))
	seed += group
	seed += str(random.randrange(1000, 9999, 1))
	check = int(seed) % 9
	seed += str(check)
	return seed


def getgroup(code):
	num , check = code[:-1], code[-1]
	if int(num) % 9 == int(check):
		pad = num[:7]
		group = pad[-1]
		return int(group)
	else:
		return False


def sendemail(member):
	message = """
		Dear Consumer:

			You have been allocated to the {team} faction,
			You need to tell us your mobile number via the following link:
			http://opshout.appspot.com/join?invitecode={invitecode}

			The Authority
		""".format(team=member['team'], invitecode=member['invitecode'])
	mail.send_mail(sender="The Authority <sam.machin@gmail.com>",
	              to=member['email'],
	              subject="Join a faction",
	              body=message)

groups  = ['red', 'blue', 'green', 'orange']

class Members(db.Model):
	msisdn = db.StringProperty()
	name = db.StringProperty()
	group = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)

class Recordings(db.Model):
	number = db.StringProperty()
	url = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)
	


class sendsms(webapp2.RequestHandler):
	def get(self):
		if users.get_current_user():
			template_values = {}
			path = os.path.join(os.path.dirname(__file__), 'sendsms.html')
			self.response.out.write(template.render(path, template_values))
		else:
	            self.redirect(users.create_login_url(self.request.uri))
	def post(self):
		if users.get_current_user():
			group = self.request.get('group')	
			message = self.request.get('message')
			query = Members.all()
			query.filter("group =", group) 
			results = query.fetch(1000)
			client = TwilioRestClient(creds.twilioaccount, creds.twiliotoken)
			for member in results:
				client.sms.messages.create(from_="+441172001500", to=member.msisdn, body=message)
		else:
			self.redirect(users.create_login_url(self.request.uri))



class join(webapp2.RequestHandler):
	def get(self):
		invitecode = self.request.get('invitecode')
		teamnum = getgroup(invitecode)
		if teamnum:
			template_values = {'invitecode' : invitecode,  'team' : groups[teamnum] }
			path = os.path.join(os.path.dirname(__file__), 'joininvite.html')
			self.response.out.write(template.render(path, template_values))
		else:
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.out.write('Invalid Invite Code')
	def post(self):
		msisdn = self.request.get('msisdn')
		invitecode = self.request.get('invitecode')
		teamnum = getgroup(invitecode)
		if teamnum:
			group = groups[teamnum]
			member = Members()
			member.msisdn = msisdn
			member.group = group
			member.put()
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.out.write('OK')
		else:
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.out.write('Invalid Invite Code')
			

class joingroup(webapp2.RequestHandler):
	def get(self):
		template_values = {}
		path = os.path.join(os.path.dirname(__file__), 'joingroup.html')
		self.response.out.write(template.render(path, template_values))
	def post(self):
		msisdn = self.request.get('msisdn')
		group = self.request.get('group')
		member = Members()
		member.msisdn = msisdn
		member.group = group
		member.put()
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write('OK')


class sendinvites(webapp2.RequestHandler):
	def get(self):
		if users.get_current_user():
			template_values = {}
			path = os.path.join(os.path.dirname(__file__), 'sendinvites.html')
			self.response.out.write(template.render(path, template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
	def post(self):
		sheetname = self.request.get('sheet')
		gc = gspread.login(creds.googleuser, creds.googlepass)
		spreadsheet = gc.open(sheetname)
		worksheet = spreadsheet.sheet1
		members = []
		for x in range(1, len(worksheet.col_values(1))):
			teamnum = worksheet.col_values(2)[x]
			member = {}
			member['email'] = worksheet.col_values(1)[x]
			member['invitecode'] = makecode(teamnum)
			member['team'] = groups[int(teamnum)]
			members.append(member)
		for member in members:
			sendemail(member)
		self.response.out.write('OK')
			
	
class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('This is The Authority')

app = webapp2.WSGIApplication([('/', MainHandler),
								('/sendsms', sendsms),
								('/joingroup', joingroup),
								('/join', join),
								('/sendinvites', sendinvites),
								],
                              debug=True)
