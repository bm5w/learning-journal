# -*- coding: utf-8 -*-
import os
import logging
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
from pyramid.view import view_config
from waitress import serve
import psycopg2
from contextlib import closing
from pyramid.events import NewRequest, subscriber
import datetime
from pyramid.httpexceptions import HTTPFound, HTTPInternalServerError, HTTPForbidden
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from cryptacular.bcrypt import BCRYPTPasswordManager
from pyramid.security import remember, forget
import markdown
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )
from zope.sqlalchemy import ZopeTransactionExtension
import json

here = os.path.dirname(os.path.abspath(__file__))

MATTLEE = "dbname=test-learning-journal user=postgres password=admin"

ON_MATTS = "C:\\Users\\jefimenko\\code_fellows\\dev_accel\\another-journal\\learning-journal\\journal.py"


# DB_SCHEMA = """
# CREATE TABLE IF NOT EXISTS entries (
#     id serial PRIMARY KEY,
#     title VARCHAR (127) NOT NULL,
#     text TEXT NOT NULL,
#     created TIMESTAMP NOT NULL
# )
# """
# INSERT_ENTRY = """
# INSERT INTO entries(title, text, created) VALUES (%s, %s, %s)
# """
# # READ_ENTRIES = """
# # SELECT * FROM entries
# # """
# SELECT_ENTRIES = """
# SELECT id, title, text, created FROM entries ORDER BY created DESC
# """

# replaces def close, open, and connect db
DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class Entry(Base):
    __tablename__ = 'entries'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.Unicode(127), nullable=False)
    text = sa.Column(sa.UnicodeText, nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    def __repr__(self):
        return u"{}: {}".format(self.__class__.__name__, self.title)

    @classmethod
    def all(cls):
        return DBSession.query(cls).order_by(cls.created.desc()).all()

    @classmethod
    def by_id(cls, id):
        return DBSession.query(cls).filter(cls.id==id).one()

    @classmethod
    def from_request(cls, request):
        title = request.params.get('title', None)
        text = request.params.get('text', None)
        created = datetime.datetime.utcnow()
        new_entry = cls(title=title, text=text, created=created)
        DBSession.add(new_entry)

    @classmethod
    def most_recent(cls):
        return DBSession.query(cls).order_by(cls.created.desc()).first()

    @classmethod
    def from_request_edit(cls, request):
        title = request.params.get('title', None)
        text = request.params.get('text', None)
        id = request.params.get('id', None)
        DBSession.query(cls).filter(cls.id == id).update({"title": title, "text": text})

logging.basicConfig()
log = logging.getLogger(__file__)

# @view_config(route_name='home', renderer='string')
# def home(request):
#     return "Hello World"


# # connect to the db
# def connect_db(settings):
#     """Return a connection to the configured database"""
#     return psycopg2.connect(settings['db'])


# # a function to initialize db
# def init_db():
#     """Create database dables defined by DB_SCHEMA

#     Warning: This function will not update existing table definitions
#     """
#     settings = {}
#     settings['db'] = os.environ.get(
#         'DATABASE_URL', 'dbname=learning-journal user=mark'
#     )

#     # For running on Matt's computer
#     if ON_MATTS == os.path.abspath(__file__):
#         settings['db'] = MATTLEE

#     with closing(connect_db(settings)) as db:
#         db.cursor().execute(DB_SCHEMA)
#         db.commit()


# @subscriber(NewRequest)
# def open_connection(event):
#     request = event.request
#     settings = request.registry.settings
#     request.db = connect_db(settings)
#     request.add_finished_callback(close_connection)


# def close_connection(request):
#     """close the database connection for this request

#     If there has been an error in the processing of the request, abort any
#     open transactions.
#     """
#     db = getattr(request, 'db', None)
#     if db is not None:
#         if request.exception is not None:
#             db.rollback()
#         else:
#             db.commit()
#         request.db.close()


# def write_entry(request):
#     """Create an entry in the db."""
#     title = request.params.get('title', None)
#     text = request.params.get('text', None)
#     created = datetime.datetime.utcnow()
#     request.db.cursor().execute(INSERT_ENTRY, (title, text, created))
#     return


UPDATE_ENTRY = """
UPDATE entries SET (title, text) = (%s, %s) WHERE id=%s
"""

SELECT_MOST_RECENT = """
SELECT id, title, text, created FROM entries ORDER BY created DESC LIMIT 1
"""

### ported to ORM, but does not update database
@view_config(route_name='new', renderer='json')
def add2_entry(request):
    """View function for adding entry, passes request to write_entry.
    If error, return HTTPInternalServerError. If not, send back to home page.
    """
    if request.authenticated_userid:
        if request.method == 'POST':
            try:
                # write_entry(request)
                Entry.from_request(request)
            except psycopg2.Error:
                # this will catch any errors generated by the database
                return HTTPInternalServerError
            # return HTTPFound(request.route_url('home'))
            # cursor = request.db.cursor()
            # cursor.execute(SELECT_MOST_RECENT)
            # keys = ('id', 'title', 'text', 'created')
            # temp = dict(zip(keys, cursor.fetchone()))
            temp = Entry.most_recent()
            # import pdb; pdb.set_trace()
            temp.created = temp.created.strftime('%b %d, %Y')
            del temp.__dict__['_sa_instance_state']
            return temp.__dict__
    else:
        return HTTPForbidden()


@view_config(route_name='home', renderer='templates/list.jinja2')
def read_entries(request):
    """Return a dictionary with entries and their data.
    Returns by creation date, most recent first.
    """
    # cursor = request.db.cursor()
    # cursor.execute(SELECT_ENTRIES)
    # keys = ('id', 'title', 'text', 'created')
    # entries = [dict(zip(keys, row)) for row in cursor.fetchall()]
    entries = Entry.all()
    return {'entries': entries}


def do_login(request):
    username = request.params.get('username', None)
    password = request.params.get('password', None)
    if not (username and password):
        raise ValueError('both username and password are required')

    settings = request.registry.settings
    manager = BCRYPTPasswordManager()
    if username == settings.get('auth.username', ''):
        hashed = settings.get('auth.password', '')
        return manager.check(hashed, password)


@view_config(route_name='login', renderer='templates/login.jinja2')
def login(request):
    """Authenticate a user by username/password"""
    username = request.params.get('username', '')
    error = ''
    if request.method == 'POST':
        error = "Login Failed"
        authenticated = False
        try:
            authenticated = do_login(request)
        except ValueError as e:
            error = str(e)
        if authenticated:
            headers = remember(request, username)
            return HTTPFound(request.route_url('home'), headers=headers)
    return {'error': error, 'username': username}


@view_config(route_name='logout')
def logout(request):
    """Logout user, remove authentication data, and redirect to home page."""
    headers = forget(request)
    return HTTPFound(request.route_url('home'), headers=headers)


SELECT_SINGLE_ENTRY = """
SELECT id, title, text, created FROM entries WHERE id=%s
"""


@view_config(route_name='detail', renderer='templates/detail.jinja2')
def entry_details(request):
    entry = Entry.by_id(request.matchdict.get('id', -1))
    del entry.__dict__['_sa_instance_state']
    entry.display_text = markdown.markdown(entry.text, extensions=['codehilite(linenums=True)', 'fenced_code'])
    return {'entry': entry, }


# ported to ORM, but does not update database
@view_config(route_name='edit', renderer='json')
def edit_entry(request):
    if request.authenticated_userid:
        if request.method == 'POST':
            try:
                Entry.from_request_edit(request)
            except psycopg2.Error:
                return HTTPInternalServerError
            text = markdown.markdown(request.params.get('text', None), extensions=['codehilite(linenums=True)', 'fenced_code'])
        return {'title': request.params.get('title', None), 'text': text}
    else:
        return HTTPForbidden()


def main():
    """Create a configured wsgi app."""
    settings = {}
    settings['reload_all'] = os.environ.get('DEBUG', True)
    settings['debug_all'] = os.environ.get('DEBUG', True)
    # settings['db'] = os.environ.get(
    #     'DATABASE_URL', 'dbname=learning-journal user=mark'
    # )
    settings['sqlalchemy.url'] = os.environ.get(
        # must be rfc1738 URL
        'DATABASE_URL', 'postgresql://mark:@localhost:5432/learning-journal'
    )
    engine = sa.engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    # Add authentication setting configuration
    settings['auth.username'] = os.environ.get('AUTH_USERNAME', 'admin')
    manager = BCRYPTPasswordManager()
    settings['auth.password'] = os.environ.get(
        'AUTH_PASSWORD', manager.encode('secret'))
    # secret value for session signing:
    secret = os.environ.get('JOURNAL_SESSION_SECRET', 'itsaseekrit')
    session_factory = SignedCookieSessionFactory(secret)
    # add a secret value for auth tkt signing
    auth_secret = os.environ.get('JOURNAL_AUTH_SECRET', 'anotherseekrit')
    # configuration setup
    config = Configurator(
        settings=settings,
        session_factory=session_factory,
        authentication_policy=AuthTktAuthenticationPolicy(
            secret=auth_secret,
            hashalg='sha512'
        ),
        authorization_policy=ACLAuthorizationPolicy(),

    )
    config.include('pyramid_jinja2')
    config.include('pyramid_tm')
    config.add_static_view('static', os.path.join(here, 'static'))
    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('detail', '/detail/{id:\d+}')
    config.add_route('edit', '/edit')
    config.add_route('new', '/new')
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
