Feature: Edit page
    Implement ability to edit and update a journal entry.

    Scenario Outline: Update an entry
        Given I want to add foo to a specific entry 1
        When edit and update an entry
        Then I see the change in its detail page, foo
