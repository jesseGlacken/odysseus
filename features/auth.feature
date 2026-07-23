Feature: Authentication

  Background:
    Given the auth system has no accounts

  Scenario: Successful login with valid credentials
    Given an admin account admin with password password123 exists
    When I log in as admin with password password123
    Then the response status code should be 200
    And the response should indicate success
    And the response should contain username admin

  Scenario: Failed login with wrong password
    Given an admin account admin with password password123 exists
    When I log in as admin with password wrongpassword
    Then the response status code should be 401

  Scenario: Get current user
    Given an admin account admin with password password123 exists
    And I am logged in as admin with password password123
    When I request the current user
    Then the response status code should be 200
    And the response should contain username admin
    And the response should indicate the user is an admin

  Scenario: Logout
    Given an admin account admin with password password123 exists
    And I am logged in as admin with password password123
    When I log out
    Then the response status code should be 200
    And the response should indicate success
