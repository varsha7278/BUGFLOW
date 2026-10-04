# BUGFLOW
# 🐞 BugFlow – Software Issue Tracking & Resolution Platform

BugFlow is a web-based Software Issue Tracking and Resolution Platform designed to help teams report, manage, track, and resolve software issues efficiently.

The platform provides issue reporting, user management, issue tracking, database integration, AI-assisted support, and Git/GitHub automation.

---

## 🚀 Project Overview

BugFlow provides a centralized platform where users can:

- Register and log in securely
- Report software issues
- Track reported issues
- View issue details
- Monitor issue status
- Manage issue severity and priority
- Use an AI Assistant for issue-related queries
- Get AI-based issue analysis and suggestions
- Detect possible duplicate issues
- Connect development activity with issue tracking through Git/GitHub

---

## ✨ Key Features

### 👤 User Management
- User registration
- User login
- Password hashing
- Role-based users
- User dashboard

### 🐞 Issue Management
- Create new issues
- Assign issue types
- Set severity and priority
- Track issue status
- Add affected module and environment
- Store reproduction steps
- View issue details
- View issues reported by users

### 🤖 AI Assistance

BugFlow includes an AI Assistant designed to help users and development teams.

#### AI Chat Assistant
Users can ask questions such as:

> "How many open issues are there?"

The assistant provides responses using the issue data available in the system.

#### AI Auto-Triage
The system can analyze a reported issue and suggest:

- Issue Type
- Severity
- Category

#### AI Duplicate Detection
The system checks existing issues to identify similar or duplicate reports.

#### AI Fix Suggestions
The system provides possible suggestions for resolving an issue.

#### AI Sprint Copilot
Provides sprint-related insights such as:

- Sprint progress
- Completion rate
- Issue status
- Remaining work

---

## 🔗 Git / GitHub Integration

BugFlow can integrate development activity with issue tracking.

Commit messages can reference issues using formats such as:

```text
fixes #9
🛠️ Technologies Used
Frontend
HTML5
CSS3
JavaScript
Jinja2 Templates
Backend
Python
Flask
SQLAlchemy
Database
PostgreSQL
Security
Password Hashing
Role-based access
AI
Rule-based AI assistance
Issue classification
Duplicate detection
Fix suggestions
Sprint insights
Development Tools
Visual Studio Code
Git
GitHub
PostgreSQL
pgAdmin / psql
📂 Project Structure
BugFlow/
│
├── app.py
├── database.py
├── models.py
├── requirements.txt
│
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── user_dashboard.html
│   ├── admin_dashboard.html
│   ├── issue_form.html
│   ├── my_issues.html
│   ├── reports.html
│   ├── sprints.html
│   └── ai_assistant.html
│
└── README.md
🗄️ Database

BugFlow uses PostgreSQL as the database.

The database stores information such as:

Users
Issues
Issue status
Issue type
Severity
Priority
Resolutions
Sprint information

SQLAlchemy is used to communicate between the Flask application and PostgreSQL database.

⚙️ Installation
1. Clone the Repository
git clone https://github.com/YOUR-USERNAME/BugFlow.git
2. Open the Project
cd BugFlow
3. Create a Virtual Environment
python -m venv .venv
4. Activate the Virtual Environment

Windows:

.venv\Scripts\activate
5. Install Dependencies
pip install -r requirements.txt
🔐 Database Configuration

Create a PostgreSQL database named:

bugflow_db

Configure the database connection using an environment variable.

Example:

DATABASE_URL=postgresql://username:password@localhost:5432/bugflow_db

Do not upload database passwords or other secrets to GitHub.

▶️ Running the Application

Start the Flask application:

python app.py

The application will run locally at:

http://127.0.0.1:8000

Open the address in a web browser.

🔌 Important API Endpoints
Authentication
POST /api/register
POST /api/login
Issues
POST /api/issues
GET /api/issues
GET /api/issues/<issue_id>
GET /api/my-issues
AI Assistant
GET  /ai-assistant
POST /api/ai/chat
POST /api/ai/triage
POST /api/ai/duplicates
POST /api/ai/suggest-fix/<issue_id>
GET  /api/ai/sprint-insights/<sprint_id>
Git Integration
POST /api/webhooks/git
Database Test
GET /api/test
🧪 Testing

BugFlow can be tested by checking:

User registration
User login
Issue creation
Issue retrieval
Database connectivity
AI Assistant
AI issue triage
Duplicate issue detection
AI fix suggestions
Sprint insights
Git webhook processing

Example:

GET /api/test

Expected result:

Backend and PostgreSQL are connected!
📊 Issue Workflow

A typical issue moves through different stages:

Reported
   ↓
Triaged
   ↓
Assigned
   ↓
In Development
   ↓
In Review
   ↓
In Testing
   ↓
Resolved

This workflow helps the development team track the complete lifecycle of an issue.
🎯 Project Objectives

The main objectives of BugFlow are:

Provide centralized issue management.
Reduce manual issue tracking.
Improve communication between users and developers.
Provide structured issue classification.
Improve issue resolution efficiency.
Use AI to assist development teams.
Connect Git/GitHub development activity with issue tracking.
Provide a scalable foundation for future software development teams.
🔮 Future Enhancements

Future versions of BugFlow can include:

Real-time notifications
Email notifications
Advanced AI integration
AI-powered root cause analysis
GitHub Actions integration
Advanced analytics dashboards
Team collaboration
File and screenshot attachments
Cloud deployment
Mobile application
Advanced role and permission management
👩‍💻 Project Team

Project: BugFlow – Software Issue Tracking & Resolution Platform

Technology: Python | Flask | PostgreSQL | SQLAlchemy | HTML | CSS | JavaScript | AI

📜 License

This project is developed for educational and academic purposes.
