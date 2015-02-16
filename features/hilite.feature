Feature: Markdown and hilite on page
    Implement ability to render markdown to html and hilite code blocks
    on detail pages.

    Scenario Outline: Go to detail page.
        Given a detail page 12
        When view it
        Then I see markdown as html and code colorized codehilite
