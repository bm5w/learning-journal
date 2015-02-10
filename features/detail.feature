Feature: Detail Page
    Implement a detailed view of a single entry with a permalink

    Scenario Outline: Click on one entry
        Given an entry time <input>
        When I click on an entry
        Then I see a one entry in detail <output>

    Examples:
    | input                        | output           |
    | 2015-02-05 23:11:10.064635   | IS this owkring? |
    | 2015-02-05 23:11:21.720433   | flsjdlfjs        |
    | 2015-02-06 00:25:14.987823   | Does this work?  |