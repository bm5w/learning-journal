# -*- coding: utf-8 -*-
from contextlib import closing
from pyramid import testing
import pytest
# from psycopg2 import DataError
# from psycopg2 import IntegrityError
import datetime
import os
from cryptacular.bcrypt import BCRYPTPasswordManager
import psycopg2

# from journal import Entry
# from journal import add2_entry
from sqlalchemy.exc import DataError, IntegrityError

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

# TEST_DSN = 'postgresql://mark:@localhost:5432/learning-journal'
TEST_DSN = 'postgresql://postgres:@localhost:5432/travis_ci_test;'

INPUT_BTN = '<input type="submit" value="Share" name="Share" />'


# connect to the db
def connect_db(settings):
    """Return a connection to the configured database"""
    return psycopg2.connect(settings['db'])


def login_helper(username, password, app):
    """encapsulate app login for reuse in tests

    Accept all status codes so that we can make assertions in tests
    """
    login_data = {'username': username, 'password': password}
    return app.post('/login', params=login_data, status='*')


def test_start_as_anonymous(app):
    response = app.get('/', status=200)
    actual = response.body
    assert INPUT_BTN not in actual


def test_login_success(app):
    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    assert redirect.status_code == 302
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    assert INPUT_BTN in actual


def test_login_fails(app):
    username, password = ('admin', 'wrong')
    response = login_helper(username, password, app)
    assert response.status_code == 200
    actual = response.body
    assert "Login Failed" in actual
    assert INPUT_BTN not in actual


def init_db(settings):
    with closing(connect_db(settings)) as db:
        db.cursor().execute(DB_SCHEMA)
        db.commit()


def clear_db(settings):
    with closing(connect_db(settings)) as db:
        db.cursor().execute("DROP TABLE entries")
        db.commit()


def clear_entries(settings):
    with closing(connect_db(settings)) as db:
        db.cursor().execute("DELETE FROM entries")
        db.commit()


def run_query(db, query, params=(), get_results=True):
    cursor = db.cursor()
    cursor.execute(query, params)
    db.commit()
    results = None
    if get_results:
        results = cursor.fetchall()
    return results


def test_write_entry(app, req_context):
    # login
    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    redirect.follow()

    fields = ('title', 'text')
    expected = ('Test Title', 'Test Text')
    entry_data = dict(zip(fields, expected))

    # assert that there are no entries when we start
    rows = run_query(req_context.db, "SELECT * FROM entries")
    assert len(rows) == 0

    app.post('/new', params=entry_data, status='2*')
    rows = run_query(req_context.db, "SELECT title, text FROM entries")
    assert len(rows) == 1
    actual = rows[0]
    for idx, val in enumerate(expected):
        assert val == actual[idx]


def test_new_entry_raise_error(app, req_context):
    # login
    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    redirect.follow()
    fields = ('title', 'text')
    expected = ('Test Title', 'Test Text')
    entry_data = dict(zip(fields, expected))
    # Test when title is greater than 127 bytes (126 characters)
    entry_data['title'] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\
    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\
    aaaaaaaaaaa"
    with pytest.raises(DataError):
        app.post('/new', params=entry_data, status='2*')

    del entry_data['title']
    with pytest.raises(IntegrityError):
        app.post('/new', params=entry_data, status='2*')

    # Test when no text is given
    del entry_data['text']
    req_context.params['title'] = "test"
    with pytest.raises(IntegrityError):
        app.post('/new', params=entry_data, status='2*')


def test_read_entries_empty(req_context):
    # call the function under test
    from journal import read_entries
    result = read_entries(req_context)

    # make assertions about the result
    assert 'entries' in result
    assert len(result['entries']) == 0


def test_read_entries(req_context):
    # prepare data for testing
    now = datetime.datetime.utcnow()
    expected = ('Test Title', 'Test Text', now)
    run_query(req_context.db, INSERT_ENTRY, expected, False)
    # call the function under test
    from journal import read_entries
    result = read_entries(req_context)
    # make assertions about the result
    assert 'entries' in result
    assert len(result['entries']) == 1
    for entry in result['entries']:
        print entry.title
        assert entry.title == expected[0]
        assert entry.text == expected[1]
        assert entry.id
        assert entry.created == now


def test_read_entries_multiple(req_context):
    """Test that read_entries method will return multiple db entries.

    Also verifies that entries are returned by creation date.
    (Most recently created returned first)
    """
    # prepare data for testing
    now3 = datetime.datetime.utcnow()
    now2 = datetime.datetime.utcnow()
    now = datetime.datetime.utcnow()
    expected = (('Test Title', 'Test Text', now),
                ('Test Title2', 'Test Text2', now2),
                ('Test Title3', 'Test Text3', now3))
    for item in expected:
        run_query(req_context.db, INSERT_ENTRY, item, False)
    # call the function under test
    from journal import read_entries
    result = read_entries(req_context)
    # make assertions about the result
    assert 'entries' in result
    assert len(result['entries']) == 3
    for index, entry in zip(range(len(expected)), result['entries']):
        assert entry.title == expected[index][0]
        assert entry.text == expected[index][1]
        assert entry.created == expected[index][2]
        assert entry.id


def test_empty_listing(app):
    """Using webtest to test body of HTML and empty db."""
    response = app.get('/')
    assert response.status_code == 200
    actual = response.body
    expected = 'No entries here so far'
    assert expected in actual


def test_listing(app, entry):
    """Using webtest to test body of HTML with entry."""
    response = app.get('/')
    assert response.status_code == 200
    actual = response.body
    for expected in entry[:1]:
        assert expected in actual


def test_post_to_add_view(auth_req, app):
    entry_data = {
        'title': 'Hello there',
        'text': 'This is a post',
    }

    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    redirect.follow()

    response = app.post('/new', params=entry_data, status='2*')

    actual = response.body

    print actual
    for expected in entry_data.values():
        assert expected in actual


# def test_post_to_add_view_2(app):
#     """Test if app.get('/add') is called returns error."""
#     entry_data = {
#         'title': 'Hello there',
#         'text': 'This is a post',
#     }
#     with pytest.raises(AppError):
#         app.get('/add', params=entry_data, status='3*')


def test_do_login_success(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'admin', 'password': 'secret'}
    assert do_login(auth_req)


def test_do_login_bad_pass(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'admin', 'password': 'wrong'}
    assert not do_login(auth_req)


def test_do_login_bad_user(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'bad', 'password': 'secret'}
    assert not do_login(auth_req)


def test_do_login_missing_params(auth_req):
    from journal import do_login
    for params in ({'username': 'admin'}, {'password': 'secret'}):
        auth_req.params = params
        with pytest.raises(ValueError):
            do_login(auth_req)


def test_logout(app):
    # re-use existing code to ensure we are logged in when we begin
    test_login_success(app)
    redirect = app.get('/logout', status="3*")
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    assert INPUT_BTN not in actual


# Fixture for webtest
@pytest.fixture(scope='function')
def app(db):
    from journal import main
    from webtest import TestApp
    os.environ['DATABASE_URL'] = TEST_DSN
    app = main()
    return TestApp(app)


# Fixture for functional test of HTML with populated db."""
@pytest.fixture(scope='function')
def entry(db, request):
    """provide a single entry in the database"""
    settings = db
    now = datetime.datetime.utcnow()
    expected = ('Test Title', 'Test Text', now)
    with closing(connect_db(settings)) as db:
        run_query(db, INSERT_ENTRY, expected, False)
        db.commit

    def cleanup():
        clear_entries(settings)

    request.addfinalizer(cleanup)

    return expected


@pytest.fixture(scope='session')
def db(request):
    """set up and tear down a database"""
    settings = {'db': TEST_DSN}
    init_db(settings)

    def cleanup():
        clear_db(settings)

    request.addfinalizer(cleanup)

    return settings


@pytest.yield_fixture(scope='function')
def req_context(db, request):
    """mock a request with a database attached"""
    settings = db
    req = testing.DummyRequest()
    with closing(connect_db(settings)) as db:
        req.db = db
        req.exception = None
        yield req

        # after a test has run, we clear out entries for isolation
        clear_entries(settings)


@pytest.fixture(scope='function')
def auth_req(request):
    manager = BCRYPTPasswordManager()
    settings = {
        'auth.username': 'admin',
        'auth.password': manager.encode('secret'),
    }
    testing.setUp(settings=settings)
    req = testing.DummyRequest()

    def cleanup():
        testing.tearDown()

    request.addfinalizer(cleanup)

    return req
