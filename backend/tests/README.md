# Tests for General Tool

This directory contains tests for the `general_tool` function in `ai_agent.py`.

## Running Tests

To run all tests:
```bash
cd backend
pytest tests/test_general_tool.py -v
```

To run tests with coverage:
```bash
cd backend
pytest tests/test_general_tool.py -v --cov=ai_agent --cov-report=term-missing --cov-branch
```

To generate HTML coverage report:
```bash
cd backend
pytest tests/test_general_tool.py --cov=ai_agent --cov-report=html
```

## Test Coverage

These tests aim for 100% statement coverage of the `general_tool` function (lines 28-52 in `ai_agent.py`).

### Test Cases Covered:

1. **Empty results**: Tests when no documents are retrieved (lines 42-43)
2. **Single document with source**: Tests document processing with source metadata (lines 47-50)
3. **Single document without source**: Tests default to 'Unknown source' when source is missing (line 48)
4. **Multiple documents**: Tests processing multiple documents and joining with separator (lines 47-52)
5. **Content truncation**: Tests truncation of content longer than 500 characters (line 49)
6. **Content at 500 chars**: Tests content exactly 500 characters (line 49)
7. **Content shorter than 500 chars**: Tests content less than 500 characters (line 49)
8. **Empty string query**: Tests with empty string query
9. **Empty metadata dict**: Tests with document that has empty metadata dict
10. **Three documents max k**: Tests that k=3 is passed to similarity_search (line 40)
11. **Response format**: Tests response formatting with proper structure (lines 50, 52)
12. **Metadata without source key**: Tests when metadata exists but 'source' key is missing (line 48)
13. **Content at 499 chars**: Tests content at 499 characters (just under limit)
14. **Content at 501 chars**: Tests content at 501 characters (just over limit, truncation)
15. **Similarity search params**: Tests that similarity_search is called with correct parameters (line 40)
16. **Empty list falsy check**: Tests that empty list is correctly identified as falsy (line 42)
17. **Response parts list building**: Tests that response_parts list is built correctly (lines 46-50)

## Requirements

Tests require:
- pytest
- pytest-cov
- pytest-mock
- langchain-core (for Document class)

Install with:
```bash
pip install -r requirements.txt
```

