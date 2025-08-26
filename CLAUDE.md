# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an intelligent business analysis system that automatically connects to Superset, captures dashboard screenshots, and uses AI to analyze business questions. The system provides a web interface where users can ask business questions and receive AI-powered analysis based on Superset dashboard data.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install

# Start the application
./start.sh
# or
python app.py
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=superset_automation --cov=app --cov=ai_analyzer --cov-report=term-missing

# Run specific test categories
pytest -m unit          # Unit tests with mocked dependencies
pytest -m integration   # Integration tests with real services
pytest -m browser       # Tests requiring browser automation
pytest -m api           # Tests requiring API access
```

### Application URLs
- Main application: http://localhost:5002
- Health check: http://localhost:5002/health

## Architecture Overview

### Core Components

1. **Flask Web Application** (`app.py`):
   - Main web server providing REST API endpoints
   - Handles user requests and coordinates analysis workflow
   - Manages async execution of Superset automation and AI analysis
   - Serves screenshots and provides health monitoring

2. **Superset Automation** (`superset_automation.py`):
   - Handles real connections to Superset instances
   - Automated login and dashboard navigation using Playwright
   - Captures screenshots of dashboards and individual charts
   - Extracts dashboard metadata and chart information
   - Implements comprehensive error handling and fallback mechanisms

3. **AI Analyzer** (`ai_analyzer.py`):
   - Integrates with BigModel.cn (via OpenAI client) for AI analysis
   - Supports both vision-based analysis (with screenshots) and text-only analysis
   - Provides business insights and recommendations based on dashboard data
   - Includes fallback templates for when AI services are unavailable

### Key Workflows

**Analysis Pipeline**:
1. User submits business question via web interface
2. System connects to Superset and captures all dashboard screenshots
3. AI analyzes screenshots and data to answer the business question
4. Results are returned with comprehensive analysis and screenshots

**Error Handling**:
- Graceful degradation when Superset is unavailable
- Fallback to mock AI analysis when API keys are missing
- Comprehensive logging and error reporting
- Timeout handling for long-running operations

### Data Flow

```
User Question → Flask App → Superset Automation → Dashboard Screenshots → AI Analyzer → Business Insights
```

## Configuration

### Environment Variables
Required environment variables (typically in `.env` file):

```env
# Superset Configuration
SUPERSET_URL=http://localhost:8088
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production

# AI API Configuration
OPENAI_API_KEY=your-bigmodel-api-key-here
OPENAI_API_BASE=https://api.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4v-plus
```

### Directory Structure
- `screenshots/` - Stores captured dashboard and chart screenshots
- `dashboard_data/` - Cached dashboard metadata and information
- `templates/` - HTML templates for the web interface
- `logs/` - Application log files

## Testing Strategy

### Test Categories
- **Unit Tests**: Mocked dependencies for fast, isolated testing
- **Integration Tests**: Real service connections for end-to-end validation
- **Browser Tests**: Playwright automation testing
- **API Tests**: External API connectivity validation

### Test Configuration
- Coverage target: 80% minimum
- Async test support with `asyncio_mode=auto`
- Comprehensive test markers for categorization
- Timeout handling for long-running tests

## Important Implementation Details

### Async/Await Pattern
The system heavily uses async/await patterns for:
- Non-blocking browser automation with Playwright
- Concurrent API calls to multiple dashboards
- Efficient resource utilization during analysis

### Error Resilience
- Multiple fallback mechanisms for each component
- Comprehensive logging at all levels
- Graceful degradation when external services are unavailable
- User-friendly error messages with troubleshooting guidance

### Security Considerations
- Environment variable management for sensitive credentials
- File path validation for screenshot serving
- Secret key management for Flask sessions
- No hardcoded credentials in source code

