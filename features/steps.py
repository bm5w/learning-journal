from lettuce import step
from lettuce import world
from lettuce import before
import re


@step('a link (\w+)')
def the_entry(step, id):
    world.detail_view = world.app.get('/')
    soup = world.detail_view.html
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
    print expected
    assert expected in world.detail_view


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

# lettuce.before.all[each_fixture][each_scenario]

# lettuce.after. (the same three possibilities