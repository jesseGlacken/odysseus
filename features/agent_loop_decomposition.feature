Feature: Agent loop decomposition

  The monolithic agent loop has been decomposed into focused sub-packages
  (loop, classifier, context, runaway, verifier, prompt).  These scenarios
  describe the observable behaviour that the decomposition must preserve.

  Scenario: Chat stream routes through the decomposed agent package
    Given the user has an active chat session
    When the user sends a streaming chat message
    Then the response is produced by the decomposed agent loop
    And the agent loop emits preparation timing events

  Scenario: Tool selection surfaces relevant tools for the request
    Given the user asks a question that needs web search
    When the agent loop prepares the turn
    Then web search tools are included in the selected tools

  Scenario: Tool execution resolves native and fenced tool calls
    Given the agent loop receives a model response with a tool call
    When the tool call is resolved
    Then the tool is executed through the verifier/execution pipeline
    And the result is appended to the conversation history

  Scenario: Completion verifier treats user instruction as untrusted data
    Given the agent used an effectful tool this turn
    When the completion verifier is invoked
    Then the verifier prompt wraps the original user instruction as untrusted context
    And a SUCCESS verdict allows the turn to finish

  Scenario: Runaway-loop detection stops repeated identical tool calls
    Given the agent has issued the same tool call many times in one turn
    When the runaway detector evaluates the call history
    Then the loop is forced to stop using tools and answer
