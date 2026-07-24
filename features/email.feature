Feature: Email

  Scenario: List email folders
    Given I am logged in as admin
    When I request email folders
    Then I receive a list of folder names
