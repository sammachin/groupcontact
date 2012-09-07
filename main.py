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
from twilio import twiml
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
import gspread



def getmembers(group, sheet):
	gc = gspread.login(creds.googleuser, creds.googlepass)
	spreadsheet = gc.open(sheet)
	worksheet = spreadsheet.sheet1
	members = []
	for x in range(1, len(worksheet.col_values(1))):
		if worksheet.col_values(2)[x] == group:
			members.append(worksheet.col_values(1)[x])
	return members
	

def getallmembers(sheet):
	gc = gspread.login(creds.googleuser, creds.googlepass)
	spreadsheet = gc.open(sheet)
	worksheet = spreadsheet.sheet1
	members = []
	for x in range(1, len(worksheet.col_values(1))):
		members.append(worksheet.col_values(1)[x])
	return members
		
		
def geturl(msgid, sheet):
	gc = gspread.login(creds.googleuser, creds.googlepass)
	spreadsheet = gc.open(sheet)
	worksheet = spreadsheet.sheet1
	url = ""
	for x in range(1, len(worksheet.col_values(1))):
		if worksheet.col_values(1)[x] == msgid:
			url = worksheet.col_values(2)[x]
	return url

		
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
			members = getmembers(group, "groups")
			client = TwilioRestClient(creds.twilioaccount, creds.twiliotoken)
			for member in members:
				client.sms.messages.create(from_="+441172001500", to=member, body=message)
			self.response.out.write("SMS sent to %s members of %s" % (str(len(members)), group))
		else:
			self.redirect(users.create_login_url(self.request.uri))


class smsall(webapp2.RequestHandler):
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
			members = getallmembers("groups")
			client = TwilioRestClient(creds.twilioaccount, creds.twiliotoken)
			for member in members:
				client.sms.messages.create(from_="+441172001500", to=member, body=message)
				self.response.out.write("SMS sent to %s members " % (str(len(members))))
		else:
			self.redirect(users.create_login_url(self.request.uri))
						
						
class groupcall(webapp2.RequestHandler):
	def get(self):
		if users.get_current_user():
			template_values = {}
			path = os.path.join(os.path.dirname(__file__), 'groupcall.html')
			self.response.out.write(template.render(path, template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
	def post(self):
		if users.get_current_user():
			group = self.request.get('group')	
			message = self.request.get('message')
			members = getmembers(group, "groups")
			client = TwilioRestClient(creds.twilioaccount, creds.twiliotoken)
			for member in members:
				client.calls.create(from_="+441172001500", to=member, url="http://opshout.appspot.com/callone?msgid=%s" % (message))
			self.response.out.write("Calls placed to %s members of %s" % (str(len(members)), group))
		else:
			self.redirect(users.create_login_url(self.request.uri))

class callone(webapp2.RequestHandler):
	def post(self):
		sheet = "recordings"
		msgid = self.request.get('msgid')
		url = geturl(msgid, sheet)
		r = twiml.Response()
		r.play(url)
		self.response.out.write(str(r))

class incommingcall(webapp2.RequestHandler):
	def post(self):
		r = twiml.Response()
		r.say("We will contact you when we are ready, do not call this number again")
		self.response.out.write(str(r))			


class recordcall(webapp2.RequestHandler):
	def get(self):
		r = twiml.Response()
		r.say("hello please record your message after the tone")
		r.record(method="POST", action="http://opshout.appspot.com/storerecording", maxLength="60", timeout="5")
		self.response.out.write(str(r))
				
				
class storerecording(webapp2.RequestHandler):
	def post(self):
		caller = self.request.get('From')	
		url = self.request.get('RecordingUrl')	
		gc = gspread.login(creds.googleuser, creds.googlepass)
		spreadsheet = gc.open("newrecordings")
		worksheet = spreadsheet.sheet1
		count = len(worksheet.col_values(1))
		worksheet.update_cell(count+1, 1, caller)
		worksheet.update_cell(count+1, 2, url)
		r = twiml.Response()
		r.say("Thankyou, goodbye")
		self.response.out.write(str(r))
						
						
						

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('This is OpShout')

app = webapp2.WSGIApplication([('/', MainHandler),
								('/sendsms', sendsms),
								('/smsmall', smsall),
								('/groupcall', groupcall),
								('/callone', callone),
								('/incommingcall', incommingcall),
								('/recordcall', recordcall),
								('/storerecording', storerecording)
								],
                              debug=True)
