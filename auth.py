import os

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class AuthorizedUser(db.Model):
    """Represents authorized users in the datastore."""
    user = db.UserProperty()

class PendingUser(db.Model):
    user = db.UserProperty()


class AuthorizedRequestHandler(webapp.RequestHandler):
   def authorize(self):
        """Return True if user is authenticated."""
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
        """Action taken for unauthenticated  user (default: go to error page)."""
        self.response.out.write("""
            <html>
              <body>
                <div>Unauthorized User</div>
                <div><a href="%s">Logout</a><br>
                <a href="/reqauth">Request Authorisation</a></div>
              </body>
            </html>""" % users.create_logout_url(self.request.uri))


class ManageAuthorizedUsers(webapp.RequestHandler):
    template_file = 'auth.html'
    def get(self):
        template_values = {
            'authorized_users': AuthorizedUser.all(),
            'pending_users': PendingUser.all(),
            }
        path = os.path.join(os.path.dirname(__file__), self.template_file)
        self.response.out.write(template.render(path, template_values))

    def post(self):
        email = self.request.get('email')
        user = users.User(email)
        auth_user = AuthorizedUser()
        auth_user.user = user
        auth_user.put()
        self.redirect('/auth/users')

class DeleteAuthorizedUser(webapp.RequestHandler):
     def get(self):
        email = self.request.get('email')
        print 'email: ', email
        user = users.User(email)
        auth_user = AuthorizedUser.gql("where user = :1", user).get()
        auth_user.delete()
        self.redirect('/auth/users')


class ApproveUser(webapp.RequestHandler):
    def get(self):
        email = self.request.get('email')
        print 'email: ', email
        user = users.User(email)
        pend_user = PendingUser.gql("where user = :1", user).get()
        pend_user.delete()
        auth_user = AuthorizedUser()
        auth_user.user = user
        auth_user.put()
        self.redirect('/auth/users')


application = webapp.WSGIApplication([('/auth/users', ManageAuthorizedUsers),
                                      ('/auth/useradd', ManageAuthorizedUsers),
                                      ('/auth/approveuser', ApproveUser),
                                      ('/auth/userdelete', DeleteAuthorizedUser)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
