"""
Tests for the general_tool function in ai_agent.py.

These tests aim for 100% statement coverage of the general_tool function
(lines 28-52 in ai_agent.py).
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set dummy API keys to avoid prompts during import
os.environ.setdefault("OPENAI_API_KEY", "test-key-openai")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-anthropic")

# Mock create_agent before importing ai_agent since it may not be available in older langchain versions
from unittest.mock import MagicMock

# Patch langchain.agents.create_agent before importing ai_agent
# ai_agent.py imports: from langchain.agents import create_agent
# We need to add create_agent to langchain.agents module if it doesn't exist
try:
    import langchain.agents as agents_module
    # Check if create_agent exists, if not add a mock version
    if not hasattr(agents_module, 'create_agent'):
        def mock_create_agent(*args, **kwargs):
            return MagicMock()
        agents_module.create_agent = mock_create_agent
except (ImportError, AttributeError):
    # If langchain.agents doesn't exist, create a mock module
    import sys
    mock_agents = MagicMock()
    mock_agents.create_agent = MagicMock(return_value=MagicMock())
    sys.modules['langchain.agents'] = mock_agents

# Import the module - we'll patch agent_manager in each test
import ai_agent


class TestGeneralTool:
    """Test suite for the general_tool function."""

    @pytest.fixture
    def sample_document_with_source(self):
        """Create a sample document with source metadata."""
        return Document(
            page_content="This is a sample document about course policies. It contains information about late penalties and grading.",
            metadata={"source": "syllabus.txt", "document_type": "syllabus"}
        )

    @pytest.fixture
    def sample_document_without_source(self):
        """Create a sample document without source metadata."""
        return Document(
            page_content="This is another document about assignments.",
            metadata={"document_type": "assignment"}
        )

    @pytest.fixture
    def long_content_document(self):
        """Create a document with content longer than 500 characters."""
        long_content = "A" * 600  # 600 characters
        return Document(
            page_content=long_content,
            metadata={"source": "lectures.txt"}
        )

    @pytest.fixture
    def exact_500_char_document(self):
        """Create a document with exactly 500 characters."""
        content = "B" * 500
        return Document(
            page_content=content,
            metadata={"source": "announcements.txt"}
        )

    @pytest.fixture
    def short_content_document(self):
        """Create a document with content shorter than 500 characters."""
        return Document(
            page_content="Short content.",
            metadata={"source": "assignments.txt"}
        )

    def test_general_tool_empty_results(self):
        """Test general_tool when no documents are retrieved.
        
        Tests line 42-43: Empty retrieved_docs case.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return empty list
            mock_search.return_value = []
            
            # Execute
            result = ai_agent.general_tool.run("What is the late policy?")
            
            # Assert - error message updated (no longer includes upload reminder)
            assert result == "I couldn't find relevant information in your course materials to answer this question."
            mock_search.assert_called_once_with("What is the late policy?", k=3)

    def test_general_tool_single_document_with_source(self, sample_document_with_source):
        """Test general_tool with a single document that has source metadata.

        Tests lines 47-50: Document processing with source in metadata.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return one document
            mock_search.return_value = [sample_document_with_source]

            # Execute
            result = ai_agent.general_tool.run("What are the course policies?")

            # Assert
            assert "From syllabus.txt:" in result
            assert sample_document_with_source.page_content in result
            mock_search.assert_called_once_with("What are the course policies?", k=3)

    def test_general_tool_single_document_without_source(self, sample_document_without_source):
        """Test general_tool with a single document without source metadata.

        Tests line 48: Default to 'Unknown source' when source is missing.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return one document without source
            mock_search.return_value = [sample_document_without_source]

            # Execute
            result = ai_agent.general_tool.run("What assignments are due?")

            # Assert
            assert "From Unknown source:" in result
            assert sample_document_without_source.page_content in result
            mock_search.assert_called_once_with("What assignments are due?", k=3)

    def test_general_tool_multiple_documents(self, 
                                              sample_document_with_source,
                                              sample_document_without_source,
                                              short_content_document):
        """Test general_tool with multiple documents.

        Tests lines 47-52: Processing multiple documents and joining with separator.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return multiple documents
            mock_search.return_value = [
                sample_document_with_source,
                sample_document_without_source,
                short_content_document
            ]

            # Execute
            result = ai_agent.general_tool.run("Tell me about the course")

            # Assert
            # Check that all documents are included
            assert "From syllabus.txt:" in result
            assert "From Unknown source:" in result
            assert "From assignments.txt:" in result

            # Check that separator is used between documents
            assert "\n\n---\n\n" in result

            # Check that content from all documents is present
            assert sample_document_with_source.page_content in result
            assert sample_document_without_source.page_content in result
            assert short_content_document.page_content in result

            # Verify the result has the expected number of separators (n-1 for n documents)
            assert result.count("\n\n---\n\n") == 2

            mock_search.assert_called_once_with("Tell me about the course", k=3)

    def test_general_tool_content_truncation_long_content(self, long_content_document):
        """Test general_tool truncates content longer than 500 characters.

        Tests line 49: Content truncation to 500 characters.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return document with long content
            mock_search.return_value = [long_content_document]

            # Execute
            result = ai_agent.general_tool.run("What is in the lectures?")

            # Assert
            # Check that source is included
            assert "From lectures.txt:" in result

            # Extract the content part (after "From lectures.txt:\n")
            content_part = result.split("From lectures.txt:\n")[1]

            # Check that content is NOT truncated anymore (uses .strip() instead of [:500])
            # Content should be full length (600 characters)
            assert len(content_part) == 600
            assert content_part == "A" * 600

            mock_search.assert_called_once_with("What is in the lectures?", k=3)

    def test_general_tool_content_exactly_500_chars(self, exact_500_char_document):
        """Test general_tool with content exactly 500 characters.

        Tests line 49: Content that's exactly 500 characters (no truncation needed).
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return document with exactly 500 characters
            mock_search.return_value = [exact_500_char_document]

            # Execute
            result = ai_agent.general_tool.run("What are the announcements?")

            # Assert - content is not truncated anymore
            assert "From announcements.txt:" in result
            content_part = result.split("From announcements.txt:\n")[1]
            assert len(content_part) == 500
            assert content_part == "B" * 500

            mock_search.assert_called_once_with("What are the announcements?", k=3)

    def test_general_tool_content_short_content(self, short_content_document):
        """Test general_tool with content shorter than 500 characters.

        Tests line 49: Content that's less than 500 characters (no truncation).
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return document with short content
            mock_search.return_value = [short_content_document]

            # Execute
            result = ai_agent.general_tool.run("What assignments are there?")

            # Assert - content is not truncated (uses .strip() now)
            assert "From assignments.txt:" in result
            assert short_content_document.page_content.strip() in result

            mock_search.assert_called_once_with("What assignments are there?", k=3)

    def test_general_tool_with_empty_string_query(self):
        """Test general_tool with empty string query."""
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return empty list
            mock_search.return_value = []

            # Execute
            result = ai_agent.general_tool.run("")

            # Assert - error message updated (no longer includes upload reminder)
            assert result == "I couldn't find relevant information in your course materials to answer this question."
            mock_search.assert_called_once_with("", k=3)

    def test_general_tool_metadata_empty_dict(self):
        """Test general_tool with document that has empty metadata dict."""
        # Create document with empty metadata
        doc = Document(
            page_content="Test content with empty metadata",
            metadata={}
        )

        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return document with empty metadata
            mock_search.return_value = [doc]

            # Execute
            result = ai_agent.general_tool.run("Test query")

            # Assert - should default to 'Unknown source' when source key is missing
            assert "From Unknown source:" in result
            assert "Test content with empty metadata" in result

            mock_search.assert_called_once_with("Test query", k=3)

    def test_general_tool_three_documents_max_k(self,
                                                 sample_document_with_source,
                                                 sample_document_without_source,
                                                 short_content_document):
        """Test general_tool respects k=3 parameter for similarity_search.

        Tests line 40: Verify that k=3 is passed to similarity_search.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return exactly 3 documents
            mock_search.return_value = [
                sample_document_with_source,
                sample_document_without_source,
                short_content_document
            ]

            # Execute
            result = ai_agent.general_tool.run("Query with k=3")

            # Assert
            # Verify k=3 was used
            mock_search.assert_called_once_with("Query with k=3", k=3)

            # Verify all 3 documents are in the result
            assert result.count("\n\n---\n\n") == 2  # 3 documents = 2 separators

    def test_general_tool_response_format(self,
                                          sample_document_with_source,
                                          sample_document_without_source):
        """Test general_tool response format is correct.

        Tests line 50 and 52: Response formatting with proper structure.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return 2 documents
            mock_search.return_value = [
                sample_document_with_source,
                sample_document_without_source
            ]

            # Execute
            result = ai_agent.general_tool.run("Format test")

            # Assert
            # Check format: "From {source}:\n{content}"
            assert result.startswith("From ")
            assert "\n" in result  # Should have newline after source
            assert "\n\n---\n\n" in result  # Should have separator between documents

            # Split by separator to get individual document parts
            parts = result.split("\n\n---\n\n")
            assert len(parts) == 2

            # Check first part format
            first_part = parts[0]
            assert first_part.startswith("From syllabus.txt:")
            assert "\n" in first_part
            source1, content1 = first_part.split("\n", 1)
            assert source1 == "From syllabus.txt:"
            assert content1 == sample_document_with_source.page_content

            # Check second part format
            second_part = parts[1]
            assert second_part.startswith("From Unknown source:")
            assert "\n" in second_part
            source2, content2 = second_part.split("\n", 1)
            assert source2 == "From Unknown source:"
            assert content2 == sample_document_without_source.page_content

    def test_general_tool_single_document_no_metadata_key(self):
        """Test general_tool when metadata exists but 'source' key is missing.

        Tests line 48: Using .get() with default value when 'source' key is missing.
        """
        # Create document with metadata but no 'source' key
        doc = Document(
            page_content="Document without source key",
            metadata={"document_type": "assignment", "other_key": "value"}
        )

        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return document
            mock_search.return_value = [doc]

            # Execute
            result = ai_agent.general_tool.run("Test query")

            # Assert - should use 'Unknown source' default
            assert "From Unknown source:" in result
            assert "Document without source key" in result
            mock_search.assert_called_once_with("Test query", k=3)

    def test_general_tool_content_at_499_chars(self):
        """Test general_tool with content at 499 characters (just under limit).

        Tests line 49: Content that's 499 characters (no truncation).
        """
        # Create document with 499 characters
        content = "C" * 499
        doc = Document(
            page_content=content,
            metadata={"source": "test.txt"}
        )

        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock
            mock_search.return_value = [doc]

            # Execute
            result = ai_agent.general_tool.run("Test query")

            # Assert - should not truncate (499 < 500)
            assert "From test.txt:" in result
            content_part = result.split("From test.txt:\n")[1]
            assert len(content_part) == 499
            assert content_part == "C" * 499

    def test_general_tool_content_at_501_chars(self):
        """Test general_tool with content at 501 characters (no truncation).

        Tests line 62: Content that's 501 characters (no truncation, uses .strip()).
        """
        # Create document with 501 characters
        content = "D" * 501
        doc = Document(
            page_content=content,
            metadata={"source": "test.txt"}
        )

        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock
            mock_search.return_value = [doc]

            # Execute
            result = ai_agent.general_tool.run("Test query")

            # Assert - should NOT truncate (uses .strip() instead of [:500])
            assert "From test.txt:" in result
            content_part = result.split("From test.txt:\n")[1]
            assert len(content_part) == 501
            assert content_part == "D" * 501

    def test_general_tool_similarity_search_called_with_correct_params(self):
        """Test that similarity_search is called with correct query and k=3.

        Tests line 40: Verify similarity_search is called with query and k=3.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return empty list (we're just testing the call)
            mock_search.return_value = []

            # Execute with various queries
            test_queries = [
                "What is the late policy?",
                "When are assignments due?",
                "Where are the lecture slides?",
                "What are the new announcements?",
            ]

            for query in test_queries:
                ai_agent.general_tool.run(query)
                mock_search.assert_called_with(query, k=3)

            # Verify it was called 4 times (once for each query)
            assert mock_search.call_count == 4

    def test_general_tool_empty_list_falsy_check(self):
        """Test that empty list [] is correctly identified as falsy.

        Tests line 42: The 'if not retrieved_docs' condition with empty list.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return empty list (explicitly)
            mock_search.return_value = []

            # Execute
            result = ai_agent.general_tool.run("Test query")

            # Assert - should return the error message for empty results
            assert result == "I couldn't find relevant information in your course materials to answer this question."
            mock_search.assert_called_once_with("Test query", k=3)

    def test_general_tool_response_parts_list_building(self):
        """Test that response_parts list is built correctly.

        Tests lines 46-50: Building the response_parts list.
        """
        # Create multiple documents
        doc1 = Document(
            page_content="First document",
            metadata={"source": "file1.txt"}
        )
        doc2 = Document(
            page_content="Second document",
            metadata={"source": "file2.txt"}
        )

        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            # Setup mock to return 2 documents
            mock_search.return_value = [doc1, doc2]

            # Execute
            result = ai_agent.general_tool.run("Test query")

            # Assert - verify both documents are in response
            assert "From file1.txt:" in result
            assert "First document" in result
            assert "From file2.txt:" in result
            assert "Second document" in result

            # Verify separator between documents
            assert result.count("\n\n---\n\n") == 1

    def test_general_tool_all_classes_k15(self, sample_document_with_source):
        """Test general_tool uses k=15 for 'all classes' queries.

        Tests line 44-45: k=15 branch for queries about all classes/courses.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            mock_search.return_value = [sample_document_with_source]

            # Test various "all classes" phrases
            test_queries = [
                "What are all my classes?",
                "Tell me about all classes",
                "Show me all courses",
                "What's due for all my classes?",
                "What are the deadlines across all courses?",
            ]

            for query in test_queries:
                ai_agent.general_tool.run(query)
                mock_search.assert_called_with(query, k=15)

            # Verify it was called 5 times (once for each query)
            assert mock_search.call_count == 5

    def test_general_tool_assignment_with_number_k5(self, sample_document_with_source):
        """Test general_tool uses k=5 for assignment queries with numbers.

        Tests line 47-48: k=5 branch for assignment queries with digits.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            mock_search.return_value = [sample_document_with_source]

            # Test various assignment queries with numbers
            test_queries = [
                "When is Assignment 3 due?",
                "What about assn 5?",
                "Tell me about hw 2",
                "When is homework 7 due?",
                "Assignment 10 deadline",
            ]

            for query in test_queries:
                ai_agent.general_tool.run(query)
                mock_search.assert_called_with(query, k=5)

            # Verify it was called 5 times (once for each query)
            assert mock_search.call_count == 5

    def test_general_tool_assignment_without_number_k3(self, sample_document_with_source):
        """Test general_tool uses k=3 for assignment queries without numbers.

        Tests line 50: k=3 default for assignment queries without digits.
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            mock_search.return_value = [sample_document_with_source]

            # Test assignment queries without numbers (should use k=3)
            test_queries = [
                "What assignments are there?",
                "Tell me about the homework",
                "When are assignments due?",
            ]

            for query in test_queries:
                ai_agent.general_tool.run(query)
                mock_search.assert_called_with(query, k=3)

            # Verify it was called 3 times (once for each query)
            assert mock_search.call_count == 3

    def test_general_tool_query_lowercase_conversion(self, sample_document_with_source):
        """Test general_tool converts query to lowercase for phrase matching.

        Tests line 41: query_lower = query.lower()
        """
        # Patch agent_manager's vector_store.similarity_search
        with patch.object(ai_agent.agent_manager.vector_store, 'similarity_search') as mock_search:
            mock_search.return_value = [sample_document_with_source]

            # Test that uppercase queries still trigger k=15 for "all classes"
            result = ai_agent.general_tool.run("ALL MY CLASSES")
            mock_search.assert_called_once_with("ALL MY CLASSES", k=15)

            # Test mixed case
            mock_search.reset_mock()
            result = ai_agent.general_tool.run("All Classes")
            mock_search.assert_called_once_with("All Classes", k=15)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=ai_agent", "--cov-report=term-missing", "--cov-branch"])
