Feature: Documents

  Scenario: Create and retrieve a document
    Given I am logged in as admin
    When I create a document with title "Test Doc"
    Then I receive a document response with that title
