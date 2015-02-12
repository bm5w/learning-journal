Feature: Detail Page
    Implement a detailed view of a single entry with a permalink

    Scenario Outline: Click on one entry
        Given a link <input>
        When I click on an entry link
        Then I see a one entry in detail <output>

    Examples:
    | input         | output           |
    | 1             | foo              |
    | 2             | flsjdlfjs        |
    | 3             | Does this work?  |
