Feature: New Page
    Implement a new entry with a permalink

    Scenario Outline: While logged in, click on new
        Given the new page and the content <input>
        When I click on the post button
        Then I see the entry with the text <output>

    Examples:
    | input                 | output         |
    | foo                   | foo            |
    | flsjdlfjs             | flsjdlfjs      |
    | Doesthiswork?         | Doesthiswork?  |
