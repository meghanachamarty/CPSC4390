# Course Sidekick Chatbot: Tool-Based Architecture & Mock Data

## Overview
This PR implements a simplified, tool-based architecture for the Course Sidekick chatbot and adds comprehensive mock course data for testing. The architecture moves away from complex MCP multi-agent setup to a single agent with specialized tools.

## Key Changes

### 1. Simplified Agent Architecture
**Before**: Complex MCP multi-agent system with separate scheduler, summary, and general agents
**After**: Single agent with multiple specialized tools

**Tools Implemented**:
- **`general_tool`**: Handles course policy questions (late penalties, grade breakdown, drops), deadline queries, resource lookup (lecture materials), and announcement tracking
- **`retrieve_context`**: General-purpose document retrieval for course materials

### 2. Mock Course Data
Created 4 comprehensive mock course documents:
- `syllabus.txt`: Course information, grading policies, late penalties, collaboration rules, regrade policies, office hours
- `assignments.txt`: All assignments with due dates, weights, descriptions, and submission requirements
- `lectures.txt`: Lecture schedule with topics, materials, Canvas locations, and key concepts
- `announcements.txt`: Course announcements with dates, important updates, and policy changes

### 3. Automatic Data Loading
- Added `load_mock_course_data()` method to `AgentManager`
- Automatically loads all `.txt` files from `mock_data/` directory on startup
- Adds metadata to identify document type and source
- Splits documents into chunks for efficient vector storage
- Graceful error handling for API quota issues

### 4. Application Lifecycle Management
- Implemented FastAPI lifespan manager
- Automatic data loading on startup
- Graceful error handling without crashing
- Ensures data is ready before serving requests

### 5. Enhanced Agent Identity
Agent now properly identifies as "Course Sidekick" and has context about:
- Purpose: AI-powered course assistant for students
- Capabilities: Policy questions, deadlines, resources, announcements
- Tool selection guidance for optimal responses

## Technical Implementation

### File Changes
- `backend/ai_agent.py`: Added `general_tool`, updated agent prompt, registered both tools
- `backend/agentmanager.py`: Added `load_mock_course_data()` method with TextLoader integration
- `backend/main.py`: Added lifespan manager for startup data loading
- `backend/mock_data/*.txt`: 4 new mock course documents
- `.gitignore`: Added `.env` to prevent API key exposure

### Architecture
```
Single Agent (Claude Sonnet 4.5)
    ├── general_tool (Course-specific Q&A)
    ├── retrieve_context (Document search)
    └── Vector Store (InMemory with OpenAI embeddings)
```

### Data Flow
1. Application starts → `lifespan()` runs
2. `load_mock_course_data()` loads all `.txt` files
3. Documents split into chunks with metadata
4. Chunks stored in vector database
5. Chatbot ready to answer questions with citations

## Testing

### Prerequisites
- Valid API keys in `.env` file:
  - `OPENAI_API_KEY`: For embeddings
  - `ANTHROPIC_API_KEY`: For LLM
  - `USER_AGENT`: Application identifier

### Running the Application
```bash
docker compose up --build
```

### Access Points
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health Check: http://localhost:8000/health

### Expected Behavior
- Application starts successfully
- Mock data loads automatically
- Chatbot recognizes course-specific queries
- Responses include citations to source documents
- Error handling for API quota issues (graceful degradation)

## Known Issues

1. **OpenAI Embeddings Quota**: If OpenAI quota is exceeded, vector store will be empty and chatbot will show "no information found" messages
2. **In-Memory Storage**: Vector store is not persistent; data is lost on restart (TODO: Add persistent database)

## Future Work

### Immediate Next Steps
- Add Canvas API integration for automatic course data fetching
- Implement `summary_tool` for generating lecture summaries
- Implement `scheduler_tool` for schedule generation based on deadlines

### Longer Term
- Migrate to persistent vector database (e.g., MongoDB Atlas Vector Search)
- Add user-specific course data management
- Implement file upload endpoints for manual document ingestion
- Add authentication and multi-user support

## Screenshots / Demo
(TBD: Add screenshots of chatbot interface and example queries)

## Related Issues
- Implements simplified architecture for easier development
- Provides mock data for testing without Canvas integration
- Lays foundation for multi-tool agent system

## Checklist
- [x] Code follows project style guidelines
- [x] Mock data created and validated
- [x] Error handling implemented
- [x] Documentation added
- [x] No breaking changes to existing functionality
- [x] API keys not committed to repository
- [ ] Tests written (TODO)
- [ ] Canvas integration (Future work)

## Notes for Reviewers
- Focus on the agent architecture simplification
- Review mock data comprehensiveness
- Check error handling for API quota issues
- Verify `.env` is properly gitignored
- Consider suggestions for additional mock data fields

