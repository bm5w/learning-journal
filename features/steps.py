from lettuce import step
from lettuce import world

from journal import entry_details

@step('an entry time (\d+)')
def the_entry(step, time):
    world.created = time

@step('I click on an entry')
def call_detail_view(step):

    world.detail_view = app.get(request.route_url('detail', id=entry.created))

@step('I see one entry in detail (\w+)')
def compare(step, expected):

    assert expected in world.detail_view
