from lettuce import step
from lettuce import world
from lettuce import before
import re


################################
# Steps for adding entries
################################
@step(u'the new page and the content (\w+)')
def new_page(step, tt):
    # from main page go to new page
    world.list_view = world.app.get('/')
    soup = world.list_view.html
    query = soup.find_all('a', text="New")
    world.link = query[0].get('href')
    world.new_page = world.app.get(world.link)

    # add content to form on new page
    world.form = world.new_page.form
    world.form['title'] = tt
    world.form['text'] = tt


@step(u'I click on the post button')
def click_post(step):
    world.new_page_detail = world.form.submit('submit').follow()


@step(u'Then I see the entry with the text (\w+)')
def compare_new(step, expected):
    assert expected in world.new_page_detail


################################
# Steps for testing detail view
################################


@step(u'a link (\w+)')
def the_entry(step, id):
    world.list_view = world.app.get('/')
    soup = world.list_view.html
    query = soup.find_all('a', 'detail', href=re.compile("/{}".format(id)))
    world.link = query[0].get('href')


@step(u'I click on an entry link')
def call_detail_view(step):
    world.detail_view = world.app.get(world.link)


@step(u'I see one entry in detail (\w+)')
def compare(step, expected):
    assert expected in world.detail_view


################################
# Steps for testing edit feature
################################


@step(u'I want to add (\w\w\w) to a specific entry, (\d)')
def add_foo(step, edit, id):
    world.edit = edit
    world.entry_id = id


@step(u'edit and update an entry')
def edit_update(step):
    # navigate from detail to edit page
    world.list_view = world.app.get('/')
    soup = world.list_view.html
    query = soup.find_all('a', href=re.compile("detail/{}".format(world.entry_id)))

    world.link = query[0].get('href')

    world.detail_page = world.app.get(world.link)
    soup = world.detail_page.html
    query = soup.find_all('a', text="Edit")

    world.link = query[0].get('href')

    world.edit_page = world.app.get(world.link)

    # get form from page, add title and text, submit and follow link
    world.form = world.edit_page.form
    world.form['title'] = world.edit
    world.form['text'] = world.edit
    world.updated_detail_page = world.form.submit('submit').follow()


@step(u'I see the change in its detail page, (\w+)')
def check_add(step, expected):
    assert expected in world.updated_detail_page.body


################################
# Steps for testing hilite feature
################################

@step(u'a detail page (\d)')
def get_detail(step, id):
    world.list_view = world.app.get('/')
    soup = world.list_view.html
    query = soup.find_all('a', 'detail', href=re.compile("/{}".format(id)))
    world.link = query[0].get('href')


@step(u'view it')
def view_detail(step):
    world.body = world.app.get(world.link).html


@step(u'I see markdown as html and code colorized (\w+)')
def check_add(step, expected):
    query = world.body.find('div', 'codehilite')
    assert query is not None


LOCAL_DSN = 'dbname=learning-journal user=mark'
TRAVIS = 'dbname=travis_ci_test user=postgres'


# Fixture for webtest
@before.all
def app():
    from journal import main
    from webtest import TestApp
    import os

    # settings = {'db': LOCAL_DSN}
    os.environ['DATABASE_URL'] = TRAVIS
    app = main()
    world.app = TestApp(app)

    # Login for testing editing
    login_data = {'username': 'admin', 'password': 'secret'}
    world.app.post('/login', params=login_data)
