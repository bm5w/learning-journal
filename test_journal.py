# -*- coding: utf-8 -*-
from contextlib import closing
from pyramid import testing
import pytest
from psycopg2 import DataError
from psycopg2 import IntegrityError
import datetime

from journal import INSERT_ENTRY
from journal import connect_db
from journal import DB_SCHEMA


TEST_DSN = 'dbname=test_learning_journal user=mark'


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


def test_write_entry(req_context):
    from journal import write_entry
    fields = ('title', 'text')
    expected = ('Test Title', 'Test Text')
    req_context.params = dict(zip(fields, expected))

    # assert that there are no entries when we start
    rows = run_query(req_context.db, "SELECT * FROM entries")
    assert len(rows) == 0

    result = write_entry(req_context)
    # manually commit so we can see the entry on query
    req_context.db.commit()

    rows = run_query(req_context.db, "SELECT title, text FROM entries")
    assert len(rows) == 1
    actual = rows[0]
    for idx, val in enumerate(expected):
        assert val == actual[idx]

    # Test when title is greater than 127 bytes (126 characters)
    req_context.params['title'] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\
    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\
    aaaaaaaaaaa"
    with pytest.raises(DataError):
        write_entry(req_context)
    # rollback cursor after above expected error
    req_context.db.rollback()
    # Test when no title is given
    del req_context.params['title']
    with pytest.raises(IntegrityError):
        write_entry(req_context)
    # rollback cursor after above expected error
    req_context.db.rollback()
    # Test when no text is given
    del req_context.params['text']
    req_context.params['title'] = "test"
    print req_context.params
    with pytest.raises(IntegrityError):
        write_entry(req_context)


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
        assert expected[0] == entry['title']
        assert expected[1] == entry['text']
        for key in 'id', 'created':
            assert key in entry


def test_read_entries_multiple(req_context):
    """Test that read_entries method will return multiple db entries.

    Also verifies that entries are returned by creation date.
    (Most recently created returned first)
    """
    # prepare data for testing
    now3 = datetime.datetime.utcnow()
    # expected = ('Test Title', 'Test Text', now)
    # run_query(req_context.db, INSERT_ENTRY, expected, False)
    now2 = datetime.datetime.utcnow()
    # expected = ('Test Title2', 'Test Text2', now)
    # run_query(req_context.db, INSERT_ENTRY, expected, False)
    now = datetime.datetime.utcnow()
    # expected = ('Test Title3', 'Test Text3', now)
    # run_query(req_context.db, INSERT_ENTRY, expected, False)
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
        assert expected[index][0] == entry['title']
        assert expected[index][1] == entry['text']
        for key in 'id', 'created':
            assert key in entry


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