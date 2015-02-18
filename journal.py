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

here = os.path.dirname(os.path.abspath(__file__))

MATTLEE = "dbname=test-learning-journal user=postgres password=admin"

ON_MATTS = "C:\\Users\\jefimenko\\code_fellows\\dev_accel\\another-journal\\learning-journal\\journal.py"


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id serial PRIMARY KEY,
    title VARCHAR (127) NOT NULL,
    text TEXT NOT NULL,
    created TIMESTAMP NOT NULL
)
"""
INSERT_ENTRY = """
INSERT INTO entries(title, text, created) VALUES (%s, %s, %s)
"""
# READ_ENTRIES = """
# SELECT * FROM entries
# """
SELECT_ENTRIES = """
SELECT id, title, text, created FROM entries ORDER BY created DESC
"""

# add this just below the SQL table definition we just created
logging.basicConfig()
log = logging.getLogger(__file__)


# @view_config(route_name='home', renderer='string')
# def home(request):
#     return "Hello World"


# connect to the db
def connect_db(settings):
    """Return a connection to the configured database"""
    return psycopg2.connect(settings['db'])


# a function to initialize db
def init_db():
    """Create database dables defined by DB_SCHEMA

    Warning: This function will not update existing table definitions
    """
    settings = {}
    settings['db'] = os.environ.get(
        'DATABASE_URL', 'dbname=learning-journal user=mark'
    )

    # For running on Matt's computer
    if ON_MATTS == os.path.abspath(__file__):
        settings['db'] = MATTLEE

    with closing(connect_db(settings)) as db:
        db.cursor().execute(DB_SCHEMA)
        db.commit()


@subscriber(NewRequest)
def open_connection(event):
    request = event.request
    settings = request.registry.settings
    request.db = connect_db(settings)
    request.add_finished_callback(close_connection)


def close_connection(request):
    """close the database connection for this request

    If there has been an error in the processing of the request, abort any
    open transactions.
    """
    db = getattr(request, 'db', None)
    if db is not None:
        if request.exception is not None:
            db.rollback()
        else:
            db.commit()
        request.db.close()


def write_entry(request):
    """Create an entry in the db."""
    title = request.params.get('title', None)
    text = request.params.get('text', None)
    created = datetime.datetime.utcnow()
    request.db.cursor().execute(INSERT_ENTRY, (title, text, created))
    return


UPDATE_ENTRY = """
UPDATE entries SET (title, text) = (%s, %s) WHERE id=%s
"""

SELECT_MOST_RECENT = """
SELECT id, title, text, created FROM entries ORDER BY created DESC LIMIT 1
"""


@view_config(route_name='new', renderer='json')
def add2_entry(request):
    """View function for adding entry, passes request to write_entry.
    If error, return HTTPInternalServerError. If not, send back to home page.
    """
    # if request.authenticated_userid:
    # else: from pyramid.httpexceptions forbidden
    if request.authenticated_userid:
        if request.method == 'POST':
            try:
                write_entry(request)
            except psycopg2.Error:
                # this will catch any errors generated by the database
                return HTTPInternalServerError
            # return HTTPFound(request.route_url('home'))
            cursor = request.db.cursor()
            cursor.execute(SELECT_MOST_RECENT)
            return dict(zip(('id', 'title', 'text', 'created'),
                        cursor.fetchone()))

    else:
        return HTTPForbidden()


@view_config(route_name='home', renderer='templates/list.jinja2')
def read_entries(request):
    """Return a dictionary with entries and their data.
    Returns by creation date, most recent first.
    """
    # import pdb; pdb.set_trace()
    cursor = request.db.cursor()
    cursor.execute(SELECT_ENTRIES)
    keys = ('id', 'title', 'text', 'created')
    entries = [dict(zip(keys, row)) for row in cursor.fetchall()]
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
    # call read entries
    # select out specific entry based on id in uri
    db_id = request.matchdict.get('id', -1)
    cursor = request.db.cursor()
    cursor.execute(SELECT_SINGLE_ENTRY, (db_id,))
    keys = ('id', 'title', 'text', 'created')
    entry = dict(zip(keys, cursor.fetchone()))
    # convert text- markdown into html
    entry['text'] = markdown.markdown(entry['text'], extensions=['codehilite(linenums=True)', 'fenced_code'])
    return {'entry': entry}


@view_config(route_name='edit', renderer='templates/edit.jinja2')
def edit_entry(request):
    if request.authenticated_userid:
        db_id = request.matchdict.get('id', -1)
        cursor = request.db.cursor()
        cursor.execute(SELECT_SINGLE_ENTRY, (db_id,))
        keys = ('id', 'title', 'text', 'created')
        entry = dict(zip(keys, cursor.fetchone()))
        if request.method == 'POST':
            try:
                db_id = request.matchdict.get('id', -1)
                title = request.params.get('title', None)
                text = request.params.get('text', None)
                request.db.cursor().execute(UPDATE_ENTRY, (title, text, db_id))
            except psycopg2.Error:
                return HTTPInternalServerError
            return HTTPFound(request.route_url('detail', id=db_id))
        return {'entry': entry}
    else:
        return HTTPForbidden()
    return {}


def main():
    """Create a configured wsgi app."""
    settings = {}
    settings['reload_all'] = os.environ.get('DEBUG', True)
    settings['debug_all'] = os.environ.get('DEBUG', True)
    settings['db'] = os.environ.get(
        'DATABASE_URL', 'dbname=learning-journal user=mark'
    )
    # For running on Matt's laptop
    if ON_MATTS == os.path.abspath(__file__):
            settings['db'] = MATTLEE

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
    config.add_static_view('static', os.path.join(here, 'static'))
    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('detail', '/detail/{id:\d+}')
    config.add_route('edit', '/edit/{id:\d+}')
    config.add_route('new', '/new')
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
