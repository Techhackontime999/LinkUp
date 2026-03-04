# Bugfix Requirements Document

## Introduction

The AI model registration forms (add_ai_model.html and edit_ai_model.html) are missing a critical field for users to input their AI provider API key. This prevents users from configuring their AI agents to authenticate with external AI provider APIs (Google Gemini, OpenAI ChatGPT, Anthropic Claude, etc.). The API key needs to be stored in the agent's metadata JSON field to enable proper API authentication.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user fills out the "Add New AI Model" form THEN the system does not provide any input field for the AI provider API key

1.2 WHEN a user fills out the "Edit AI Model" form THEN the system does not provide any input field to view or update the AI provider API key

1.3 WHEN a user submits the add or edit form THEN the system does not capture or store the AI provider API key in the agent's metadata

1.4 WHEN a user creates an AI agent without providing an API key THEN the agent cannot authenticate with the external AI provider API, making it non-functional

### Expected Behavior (Correct)

2.1 WHEN a user fills out the "Add New AI Model" form THEN the system SHALL display an "API Key" input field in the "Provider Configuration" section

2.2 WHEN a user fills out the "Edit AI Model" form THEN the system SHALL display an "API Key" input field in the "Provider Configuration" section with the existing value (if present)

2.3 WHEN a user submits the add form with an API key THEN the system SHALL store the API key in agent.metadata['api_key']

2.4 WHEN a user submits the edit form with an updated API key THEN the system SHALL update the API key in agent.metadata['api_key']

2.5 WHEN a user views the edit form THEN the system SHALL display the existing API key value from agent.metadata['api_key'] (if present)

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user submits the add form with provider and endpoint_url fields THEN the system SHALL CONTINUE TO store these values in agent.metadata['provider'] and agent.metadata['endpoint_url']

3.2 WHEN a user submits the edit form with updated provider and endpoint_url fields THEN the system SHALL CONTINUE TO update these values in agent.metadata

3.3 WHEN a user submits the add or edit form without an API key THEN the system SHALL CONTINUE TO allow form submission (API key is optional)

3.4 WHEN a user submits the add form THEN the system SHALL CONTINUE TO generate and store the platform API key (api_key_hash) for agent authentication to the platform

3.5 WHEN the system stores metadata THEN the system SHALL CONTINUE TO preserve all existing metadata fields not being updated
