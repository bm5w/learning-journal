from lettuce import step
from lettuce import world
from lettuce import before
import re


@step('a link (\w+)')
def the_entry(step, id):
    world.list_view = world.app.get('/')
    soup = world.list_view.html
    # print soup.prettify()
    # print soup.find_all('a', 'detail')
    query = soup.find_all('a', 'detail', href=re.compile("/{}".format(id)))
    world.link = query[0].get('href')
    # for link in soup.find_all('a', 'detail'):
    #     world.links.append(link.get('href'))
    #     print link.get('href')


@step('I click on an entry link')
def call_detail_view(step):
    world.detail_view = world.app.get(world.link)


@step('I see a one entry in detail (\w+)')
def compare(step, expected):
    assert expected in world.detail_view


################################
# Steps for testing edit feature
################################

@step('I want to add (\w\w\w) to a specific entry (\d)')
def add_foo(step, edit, id):
    world.edit = edit
    world.entry_id = id


@step('edit and update an entry')
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

    # put world.edit into text'
    soup = world.edit_page.html
    query = soup.find_all('form')
    print 'on edit'
    print query[0]

    new_stuff = {}
    new_stuff['title'] = world.edit
    new_stuff['text'] = world.edit
    world.updated_detail_page = world.app.post(query[0].get('action'), params=new_stuff).follow()



@step('I see the change in its detail page, (\w+)')
def check_add(step, expected):
    print expected
    assert expected in world.updated_detail_page.body




LOCAL_DSN = 'dbname=learning-journal user=mark'


# Fixture for webtest
@before.all
def app():
    from journal import main
    from webtest import TestApp
    import os

    # settings = {'db': LOCAL_DSN}
    os.environ['DATABASE_URL'] = LOCAL_DSN
    print os.environ['DATABASE_URL']
    app = main()
    world.app = TestApp(app)

    # Login for testing editing
    login_data = {'username': 'admin', 'password': 'secret'}
    world.app.post('/login', params=login_data)

# lettuce.before.all[each_fixture][each_scenario]

# lettuce.after. (the same three possibilities