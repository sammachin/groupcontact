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
from google.appengine.api import taskqueue
import os
from google.appengine.ext.webapp import template
import sys
import string
import unicodedata, re
import urllib
import gspread
import json



def getmembers(group, sheet):
	gc = gspread.login(creds.googleuser, creds.googlepass)
	spreadsheet = gc.open(sheet)
	worksheet = spreadsheet.sheet1
	cell_list = worksheet.findall(group)
	numbers = worksheet.range('A2:A%s' % len(worksheet.col_values(1)))
	members = []
	for cell in cell_list:
		x = cell.row -2
		members.append(numbers[x].value)
	return members
	
	
def getallmembers(sheet):
	gc = gspread.login(creds.googleuser, creds.googlepass)
	spreadsheet = gc.open(sheet)
	worksheet = spreadsheet.sheet1
	numbers = worksheet.range('A2:A%s' % len(worksheet.col_values(1)))
	members = []
	for number in numbers:
		members.append(number.value)
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


class AuthorizedUser(db.Model):
	user = db.UserProperty()

class PendingUser(db.Model):
	user = db.UserProperty()


class AuthorizedRequestHandler(webapp2.RequestHandler):
	def authorize(self):
		user = users.get_current_user()
		if not user:
			self.not_logged_in()
		else:
			auth_user = AuthorizedUser.gql("where user = :1", user).get()
			if not auth_user:
				self.unauthorized_user()
			else:
				return True
	def not_logged_in(self):
		self.redirect(users.create_login_url(self.request.uri))
	def unauthorized_user(self):
		self.response.out.write("""
	           	<html>
	              <body>
	                <div>Unauthorized User</div>
	                <div><a href="%s">Logout</a><br>
	                <a href="/reqauth">Request Authorisation</a></div>
	              </body>
	            </html>""" % users.create_logout_url(self.request.uri))


class ReqAuth(webapp2.RequestHandler):
     def get(self):
        user = users.get_current_user()
        auth_user = PendingUser()
        auth_user.user = user
        auth_user.put()
        self.response.out.write('Access requested for ' + str(user))
	
	
class submitmessages(AuthorizedRequestHandler):
	def post(self):
		memberslist = self.request.get('members')	
		members = json.loads(memberslist)
		message = self.request.get('message')
		client = TwilioRestClient(creds.twilioaccount, creds.twiliotoken)
		for member in members:
			client.sms.messages.create(from_=creds.smsnumber, to=member, body=message)
		
class makecalls(AuthorizedRequestHandler):
	def post(self):
		memberslist = self.request.get('members')	
		members = json.loads(memberslist)
		message = self.request.get('message')
		client = TwilioRestClient(creds.twilioaccount, creds.twiliotoken)
		for member in members:
			client.calls.create(from_=creds.voicenumber, to=member, url="http://opshout.appspot.com/callone?msgid=%s" % (message))


class sendsms(AuthorizedRequestHandler):
	def get(self):
		if self.authorize():
			template_values = {}
			path = os.path.join(os.path.dirname(__file__), 'sendsms.html')
			self.response.out.write(template.render(path, template_values))
	def post(self):
		if self.authorize():
			group = self.request.get('group')	
			message = self.request.get('message')
			members = getmembers(group, "groups")
			taskqueue.add(url='/submitmessages', params = {'members': json.dumps(members), 'message' : message})
			self.response.out.write("SMS sent to %s members of %s" % (str(len(members)), group))

class sendsmsall(AuthorizedRequestHandler):
	def get(self):
		if users.get_current_user():
			template_values = {}
			path = os.path.join(os.path.dirname(__file__), 'sendsmsall.html')
			self.response.out.write(template.render(path, template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
	def post(self):
		if users.get_current_user():
			message = self.request.get('message')
			members = getallmembers("groups")
			taskqueue.add(url='/submitmessages', params = {'members': json.dumps(members), 'message' : message})
			self.response.out.write("SMS sent to %s members" % (str(len(members))))
		else:
			self.redirect(users.create_login_url(self.request.uri))
											
class groupcall(AuthorizedRequestHandler):
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
			taskqueue.add(url='/makecalls', params = {'members': json.dumps(members), 'message' : message})
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

class incommingsms(webapp2.RequestHandler):
	def post(self):
		r = twiml.Response()
		r.sms("We will contact you when we are ready, do not text this number again")
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
								('/groupcall', groupcall),
								('/sendsmsall', sendsmsall),
								('/callone', callone),
								('/incommingcall', incommingcall),
								('/incommingsms', incommingsms),
								('/recordcall', recordcall),
								('/storerecording', storerecording),
								('/submitmessages', submitmessages),
								('/makecalls', makecalls),
								('/reqauth', ReqAuth)
								],
                              debug=True)
