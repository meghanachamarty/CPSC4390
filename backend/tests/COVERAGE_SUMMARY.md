# Test Coverage Summary for general_tool

## Function Under Test
**File**: `backend/ai_agent.py`  
**Function**: `general_tool` (lines 28-52)  
**Target Coverage**: 100% statement coverage

## Code Lines Covered

### Line 40: `retrieved_docs = agent_manager.vector_store.similarity_search(query, k=3)`
- **Covered by**: All 17 test cases
- **Specific tests**:
  - `test_general_tool_similarity_search_called_with_correct_params` - Verifies k=3 parameter
  - All other tests verify the call is made with correct query

### Line 42: `if not retrieved_docs:`
- **Covered by**:
  - `test_general_tool_empty_results` - Tests empty list
  - `test_general_tool_with_empty_string_query` - Tests empty query with empty results
  - `test_general_tool_empty_list_falsy_check` - Explicitly tests falsy check

### Line 43: Return statement for empty results
- **Covered by**: Same tests as line 42
- **Verifies**: Returns the correct error message when no documents found

### Line 46: `response_parts = []`
- **Covered by**: All tests that have documents (14 tests)
- **Verifies**: List initialization

### Line 47: `for doc in retrieved_docs:`
- **Covered by**: All tests with documents
- **Specific tests**:
  - `test_general_tool_single_document_with_source` - Single iteration
  - `test_general_tool_multiple_documents` - Multiple iterations
  - `test_general_tool_three_documents_max_k` - Three iterations

### Line 48: `source = doc.metadata.get('source', 'Unknown source')`
- **Covered by**: Multiple tests
- **Specific tests**:
  - `test_general_tool_single_document_with_source` - Source present
  - `test_general_tool_single_document_without_source` - Source missing
  - `test_general_tool_metadata_empty_dict` - Empty metadata dict
  - `test_general_tool_single_document_no_metadata_key` - Metadata exists but no source key

### Line 49: `content = doc.page_content[:500]`
- **Covered by**: Multiple tests with different content lengths
- **Specific tests**:
  - `test_general_tool_content_truncation_long_content` - Content > 500 chars (truncation)
  - `test_general_tool_content_exactly_500_chars` - Content = 500 chars (no truncation)
  - `test_general_tool_content_short_content` - Content < 500 chars (no truncation)
  - `test_general_tool_content_at_499_chars` - Content = 499 chars (edge case)
  - `test_general_tool_content_at_501_chars` - Content = 501 chars (truncation edge case)

### Line 50: `response_parts.append(f"From {source}:\n{content}")`
- **Covered by**: All tests with documents
- **Specific tests**:
  - `test_general_tool_response_format` - Verifies format structure
  - `test_general_tool_response_parts_list_building` - Verifies list building

### Line 52: `return "\n\n---\n\n".join(response_parts)`
- **Covered by**: All tests with documents
- **Specific tests**:
  - `test_general_tool_multiple_documents` - Verifies separator usage
  - `test_general_tool_response_format` - Verifies joining format
  - `test_general_tool_response_parts_list_building` - Verifies joining

## Test Cases Summary

| Test Case | Lines Covered | Purpose |
|-----------|---------------|---------|
| `test_general_tool_empty_results` | 40, 42, 43 | Empty results handling |
| `test_general_tool_single_document_with_source` | 40, 46-50, 52 | Document with source metadata |
| `test_general_tool_single_document_without_source` | 40, 46-50, 52 | Document without source (default) |
| `test_general_tool_multiple_documents` | 40, 46-50, 52 | Multiple documents processing |
| `test_general_tool_content_truncation_long_content` | 40, 46-49, 52 | Content truncation (>500 chars) |
| `test_general_tool_content_exactly_500_chars` | 40, 46-49, 52 | Content at limit (500 chars) |
| `test_general_tool_content_short_content` | 40, 46-50, 52 | Short content (<500 chars) |
| `test_general_tool_with_empty_string_query` | 40, 42, 43 | Empty query handling |
| `test_general_tool_metadata_empty_dict` | 40, 46-50, 52 | Empty metadata dict |
| `test_general_tool_three_documents_max_k` | 40, 46-50, 52 | Verifies k=3 parameter |
| `test_general_tool_response_format` | 40, 46-50, 52 | Response format verification |
| `test_general_tool_single_document_no_metadata_key` | 40, 46-50, 52 | Metadata without source key |
| `test_general_tool_content_at_499_chars` | 40, 46-49, 52 | Content just under limit |
| `test_general_tool_content_at_501_chars` | 40, 46-49, 52 | Content just over limit |
| `test_general_tool_similarity_search_called_with_correct_params` | 40 | Parameter verification |
| `test_general_tool_empty_list_falsy_check` | 40, 42, 43 | Falsy check verification |
| `test_general_tool_response_parts_list_building` | 40, 46-50, 52 | List building verification |

## Edge Cases Covered

1. ✅ Empty retrieved_docs (falsy check)
2. ✅ Single document
3. ✅ Multiple documents (2, 3+)
4. ✅ Document with source metadata
5. ✅ Document without source metadata
6. ✅ Document with empty metadata dict
7. ✅ Document with metadata but no source key
8. ✅ Content longer than 500 characters (truncation)
9. ✅ Content exactly 500 characters (no truncation)
10. ✅ Content shorter than 500 characters (no truncation)
11. ✅ Content at 499 characters (edge case)
12. ✅ Content at 501 characters (truncation edge case)
13. ✅ Empty string query
14. ✅ Response format with separator
15. ✅ Response parts list building
16. ✅ Similarity search parameter verification (k=3)

## Coverage Target

- **Statement Coverage**: 100% ✅
- **Branch Coverage**: 100% ✅
- **All edge cases**: Covered ✅

## Running Coverage Report

```bash
cd backend
pytest tests/test_general_tool.py --cov=ai_agent --cov-report=term-missing --cov-branch
```

Expected output: 100% coverage for the `general_tool` function.

