"""
Object-oriented LLM provider layer (BaseLLMProvider + circuit breaker +
traffic control + error mapping), tested via
tests/services/llm/test_base_provider.py and test_routing_provider.py.

Not currently the call path for production traffic — deeptutor.services.llm.factory
(the actual chokepoint) calls deeptutor.services.llm.executors' sdk_complete/
sdk_stream directly. This package predates that and was left with a
ModuleNotFoundError (providers/anthropic.py importing a nonexistent
..http_client) and no __init__.py, meaning it silently could not be
imported at all.
"""
