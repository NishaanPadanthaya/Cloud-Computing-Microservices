# Microservices Integration Project

This project integrates three microservices:
1. Bug Tracker
2. Code Review
3. Calendar

## Architecture

The system consists of the following components:

- **Bug Tracker Service**: Manages bug reports and assignments
- **Code Review Service**: Handles code review requests and feedback
- **Calendar Service**: Provides scheduling and event management
- **MongoDB**: Shared database for all services
- **Docker**: Containerization for easy deployment

## Integration Features

- Bug reports automatically create calendar events
- Code reviews automatically create calendar events
- Calendar provides a unified view of all activities
- Services communicate via REST APIs

## Prerequisites

- Docker and Docker Compose
- Node.js (for local development)
- Python 3.8+ (for local development)

## Getting Started

1. Clone the repository:
   ```
   git clone <repository-url>
   cd Microservices
   ```

2. Start all services using Docker Compose:
   ```
   docker-compose up -d
   ```

3. Access the services:
   - Bug Tracker: http://localhost:8000
   - Code Review: http://localhost:8001
   - Calendar API: http://localhost:5000
   - Calendar Client: http://localhost:3000

## API Documentation

### Bug Tracker Service
- `POST /client/bugs/create`: Create a new bug
- `GET /manager/bugs`: List all bugs
- `POST /manager/bugs/assign`: Assign a bug to an employee

### Code Review Service
- `POST /reviews/`: Create a new code review
- `GET /reviews/`: List all code reviews
- `PUT /reviews/{review_id}`: Update a code review

### Calendar Service
- `GET /api/events`: Get all events
- `POST /api/events`: Create a new event
- `GET /api/events/bugs`: Get all bug-related events
- `GET /api/events/code-reviews`: Get all code review-related events

## Development

To run services individually for development:

### Bug Tracker
```
cd bug_tracker
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Code Review
```
cd code_review
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Calendar Service
```
cd calendar
npm install
npm start
```

### Calendar Client
```
cd calendar/client
npm install
npm start
```

## Troubleshooting

- If services can't connect to MongoDB, ensure the MongoDB container is running
- Check the logs for each service: `docker-compose logs <service-name>`
- Ensure all required environment variables are set in the .env files or docker-compose.yml
