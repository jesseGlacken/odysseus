Feature: Chat

  Scenario: Create a chat session
    Given I am logged in as admin
    When I send a chat message "Hello"
    Then I receive a response text
