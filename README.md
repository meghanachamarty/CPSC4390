# CourseKey

CourseKey helps students quickly find and organize critical course information. Instead of searching through scattered documents and platforms, it provides a unified dashboard and AI-powered chat for streamlined access.

[Visit CourseKey](https://coursekey.onrender.com)

---

## Features

* **Chatbot Q\&A**: Ask natural-language questions; responses cite original sources.
* **Summaries**: Auto-generate lecture summaries, outlines, glossaries, and key takeaways.
* **Deadlines Aggregator**: Extract due dates, weights, and export as CSV/iCal.
* **Study Aids**: Generate study guides, reference sheets, practice prompts.
* **Dashboard**: Weekly checklist, workload planner, announcements digest.

---

## Tech Stack

* **Backend**: Python (FastAPI), modular agent-based architecture
* **Frontend**: React (JavaScript) for chat + dashboard UI
* **Data**: MongoDB (storage), AWS S3 (file storage)
* **AI/LLM APIs**: AWS Bedrock or Azure AI Foundry
* **Containerization**: Docker for deployment & portability
---

## Getting Started

### Running the Standalone Application

For instructions on running the project locally with Docker Compose, see the [Getting Started Locally guide](documentation/doc1.md).

### Running as a Browser Extension

CourseKey can also run as a browser extension that integrates directly with Canvas. The extension appears as a collapsible sidebar on Canvas pages.

#### Prerequisites

1. **Backend and Frontend Running**: 
   - Backend must be running on `http://localhost:8000`
   - Frontend must be running on `http://localhost:3000`
   - **Start both services separately** (see instructions below)

2. **Browser**: Chrome, Edge, or Firefox (Chrome recommended for development)

#### Starting Backend and Frontend

For extension development, you need to run backend and frontend separately:

**Terminal 1 - Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm start  # Runs on port 3000
```

**Note:** The single unified `Dockerfile` is for production deployment and won't work for extension development since it serves everything on port 80. For development, run the services separately as shown above.

#### Quick Setup

1. **Load the Extension in Chrome**:
   - Navigate to `chrome://extensions/`
   - Enable "Developer mode" (toggle in top-right)
   - Click "Load unpacked"
   - Select the `extension/` folder from this project

2. **Navigate to Canvas**:
   - Go to any Canvas page (e.g., `https://canvas.yale.edu`)
   - Look for the floating chat button (💬) in the bottom-right corner
   - Click it to open the CourseKey sidebar

#### Extension Features

- **Collapsible Sidebar**: Appears on all Canvas pages with a toggle button
- **Fullscreen Mode**: Expand chat to fullscreen for focused conversations
- **Minimize**: Return from fullscreen to sidebar view
- **Keyboard Shortcuts**: 
  - `Ctrl/Cmd + K` - Toggle sidebar
  - `Esc` - Close fullscreen
- **Chat Persistence**: Chat history is maintained when switching between sidebar and fullscreen
- **New Chat Button**: Clear chat history and start fresh anytime
- **Auto-Refresh**: Chat clears on page refresh for a clean start

#### How It Works

The extension injects a sidebar widget into Canvas pages that loads the React app in an iframe. The sidebar can be:
- **Collapsed**: Hidden with only a floating toggle button visible
- **Expanded**: Sidebar visible with the chatbot interface
- **Fullscreen**: Expanded to a fullscreen overlay for larger conversations

#### File Structure

```
extension/
├── manifest.json          # Extension configuration
├── content-script.js      # Injects sidebar into Canvas pages
├── content-styles.css     # Styles for sidebar and fullscreen
├── background.js          # Extension service worker
└── README.md             # Detailed extension documentation
```

For detailed setup instructions, troubleshooting, and customization options, see the [Extension README](extension/README.md).

---

## Testing

CourseKey maintains comprehensive test coverage for backend functionality. Each component has its own test suite. Below are the test coverage details for each tested component.

### Coverage Target

**Project Requirement**: At least 80% Statement Coverage for backend and frontend code (per project specification)

---

### `general_tool` Function Tests

Tests for the `general_tool` function which handles course document retrieval and query processing.

**Test Coverage**:
- **Statement Coverage**: 100%
- **Branch Coverage**: 100%
- **Test File**: `backend/tests/test_general_tool.py`
- **Function Under Test**: `general_tool` in `backend/ai_agent.py`
- **Number of Tests**: 21 test cases

**Running the Tests**:

From the `backend` directory:
```bash
cd backend
python3 -m pytest tests/test_general_tool.py -v
```

Run with detailed coverage report:
```bash
cd backend
python3 -m pytest tests/test_general_tool.py --cov=ai_agent --cov-report=term-missing --cov-branch -v
```

Generate HTML coverage report:
```bash
cd backend
python3 -m pytest tests/test_general_tool.py --cov=ai_agent --cov-report=html
# Open htmlcov/index.html in your browser to view the report
```

**What These Tests Cover**:
- Empty result handling
- Single and multiple document retrieval
- Content truncation and length handling
- Source metadata extraction
- Adaptive `k` parameter selection for different query types:
  - `k=15` for "all classes/courses" queries
  - `k=5` for assignment queries with numbers
  - `k=3` for general queries
- Query processing and formatting
- Edge cases (empty metadata, missing source keys, various content lengths)

### `scheduler_tool` Tests

Tests for the `scheduler_tool` function which powers the Scheduler Agent workflow defined in the second half of `backend/ai_agent.py`.

**Test Coverage Highlights**:
- Builds plans directly from `backend/mock_data/assignments.txt` (Assignments 3-6) to ensure the mock data drives the schedule output.
- Validates task normalization, weekly distributions, reminder generation, and study block recommendations.
- Confirms user preferences (e.g., weekend-only study days) are enforced.
- Test File: `backend/tests/test_scheduler_tool.py`

**Running the Tests**:

From the `backend` directory:
```bash
cd backend
python3 -m pytest tests/test_scheduler_tool.py -v
```

**What These Tests Cover**:
- Structured plan creation for Assignments 3 and 4 using their actual mock-data due dates.
- Reminder output, task-overview metadata, and aggregate workload calculations.
- Preferred day filtering (weekend-only example) and study block recommendations.

#### Manual Scheduler Agent Verification (OpenAI)

The Scheduler Agent uses `openai:gpt-4o-mini` via LangChain’s `init_chat_model`. To run a full end-to-end test (and generate a real OpenAI call) using the mock assignments:

1. Export your API keys (or create a `.env`) so both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are available.
2. From the `backend` folder, run:
   ```bash
   cd backend
   python3 - <<'PY'
import json
from ai_agent import agent_manager, scheduler_agent

agent_manager.load_mock_course_data()  # Ensure mock docs are available

payload = {
    "week_start": "2025-11-03",
    "todos": [
        {
            "title": "Assignment 3: Control Flow and Loops",
            "course": "CS 101",
            "due_date": "2025-11-05T23:59:00",
            "estimated_hours": 4,
            "priority": "urgent"
        },
        {
            "title": "Assignment 4: Functions and Modules",
            "course": "CS 101",
            "due_date": "2025-11-12T23:59:00",
            "estimated_hours": 3,
            "priority": "high"
        }
    ],
    "user_preferences": {
        "preferred_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "max_hours_per_day": 5,
        "study_block_minutes": 60,
        "notification_channels": ["push", "email"],
        "reminder_offsets": [3, 1]
    }
}

response = scheduler_agent.invoke({"input": json.dumps(payload)})
print(response)
PY
   ```
3. Inspect the returned summary for workload highlights, study block guidance, and reminders. This run confirms the LLM makes an OpenAI call and that the mock assignments drive the generated plan.

### Frontend Tests

Tests for the React frontend application covering UI rendering, WebSocket communication, and user interactions.

**Test Coverage**:
- **Statement Coverage**: 85.26%
- **Branch Coverage**: 80.43%
- **Function Coverage**: 86.66%
- **Line Coverage**: 85.39%
- **Test File**: `frontend/src/App.test.js`
- **Component Under Test**: `App.js`
- **Number of Tests**: 7 test cases

**Running the Tests**:

From the `frontend` directory:
```bash
cd frontend
npm test -- --coverage --watchAll=false
```

**What These Tests Cover**:
- Header message rendering from `/hello` endpoint
- Fetch error handling
- WebSocket URL selection (localhost vs backend)
- AI response streaming with echo/duplicate filtering
- Final sentinel (`[[FINAL]]`) handling
- WebSocket error logging
- Send button disabled state and Enter key functionality
- WebSocket connection state validation

---

_Note: Other team members will add their test coverage sections for their respective components._

---

## Multi-Armed Bandit Experimentation (Metrics Milestone)

CourseKey implements a **Multi-Armed Bandit (MAB)** algorithm to automatically optimize the "Send" button design based on user click rates. This allows the application to dynamically find and serve the best-performing button variant without traditional A/B testing limitations.

### Implementation Overview

**Algorithm**: Epsilon-Greedy Multi-Armed Bandit
- **Exploration (ε = 10%)**: Randomly tries all variants to gather data
- **Exploitation (90%)**: Shows the variant with highest conversion rate
- **Adaptive**: Automatically shifts traffic to better-performing variants over time

### Button Variants

Three variations of the Send button are tested:

1. **Variant A** (Baseline): Purple-blue gradient
   - `background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
   - Standard size and styling

2. **Variant B** (Color variation): Green gradient
   - `background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%)`
   - Same size as Variant A, different color scheme

3. **Variant C** (Color + size variation): Pink-red gradient
   - `background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)`
   - Slightly larger button (14px/32px padding vs 12px/28px)
   - Larger font size (16px vs 15px)

### How It Works

1. **User Visit**: When a user loads the page, the frontend requests a button variant from `/api/bandit/variant`
2. **Variant Assignment**: Backend uses epsilon-greedy algorithm to select variant (10% random, 90% best performer)
3. **Impression Tracking**: Backend records that the variant was shown
4. **Conversion Tracking**: When user clicks the button, frontend sends conversion event to `/api/bandit/conversion`
5. **Auto-Optimization**: Algorithm updates conversion rates and automatically shifts more traffic to better performers

### API Endpoints

- `GET /api/bandit/variant` - Get which variant to show (automatically tracks impression)
- `POST /api/bandit/conversion` - Record a button click for a variant
- `GET /api/bandit/stats` - View current statistics for all variants (for monitoring)

### Code Location

- **Algorithm**: `backend/bandit/algorithm.py` - Epsilon-greedy MAB implementation
- **API Endpoints**: `backend/main.py` - Bandit endpoints (lines 99-141)
- **Frontend Integration**: `frontend/src/App.js` - Variant fetching and click tracking
- **Button Styles**: `frontend/src/App.css` - CSS for variants A, B, and C

### Advantages Over Traditional A/B Testing

- **Adaptive**: Doesn't waste traffic on poor performers
- **Fast Optimization**: Quickly identifies and promotes winners
- **Continuous Learning**: Always exploring to find better variants
- **Real-time**: No fixed experiment duration needed

### Monitoring

Check current variant performance:
```bash
curl http://localhost:8000/api/bandit/stats
```

Response includes:
- `best_variant`: Currently top-performing variant
- `stats`: Detailed metrics (clicks, impressions, conversion rate) for each variant

### Resources

- [Multi-Armed Bandit vs A/B Testing](http://stevehanov.ca/blog/index.php?id=132)
- [Bandit Algorithms Explained](https://www.chrisstucchio.com/blog/2012/bandit_algorithms_vs_ab.html)
