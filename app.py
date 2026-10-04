from functools import wraps
import traceback
import csv
import io
import re
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

from database import Base, SessionLocal, engine
from models import (
    User,
    Issue,
    IssueType,
    Severity,
    Priority,
    IssueStatus,
    Sprint,
    SprintStatus,
    AuditLog
)

# ==========================================================
# FLASK APP
# ==========================================================

app = Flask(__name__)

# Needed for sessions to work. In production, load this from
# an environment variable instead of hardcoding it.
app.secret_key = "change-this-to-a-random-secret-key"

# ==========================================================
# CREATE DATABASE TABLES
# ==========================================================

Base.metadata.create_all(bind=engine)


# ==========================================================
# AUTH DECORATORS
# ==========================================================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "message": "Login required"
            }), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "message": "Login required"
            }), 401

        if session.get("role") != "admin":
            return jsonify({
                "message": "Admin access required"
            }), 403

        return f(*args, **kwargs)
    return wrapper


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def issue_to_dict(issue):

    return {
        "id": issue.id,

        "issue_key": issue.issue_key,

        "issue_type":
            issue.issue_type.value
            if issue.issue_type else None,

        "title": issue.title,

        "description": issue.description,

        "reproduction_steps":
            issue.reproduction_steps,

        "status":
            issue.status.value
            if issue.status else None,

        "severity":
            issue.severity.value
            if issue.severity else None,

        "priority":
            issue.priority.value
            if issue.priority else None,

        "affected_module":
            issue.affected_module,

        "environment":
            issue.environment,

        "project_key":
            issue.project_key,

        "reporter_id":
            issue.reporter_id,

        "assignee_id":
            issue.assignee_id,

        "sprint_id":
            getattr(issue, "sprint_id", None),

        "created_at":
            issue.created_at.isoformat()
            if issue.created_at else None,

        "updated_at":
            issue.updated_at.isoformat()
            if issue.updated_at else None,

        "resolved_at":
            issue.resolved_at.isoformat()
            if issue.resolved_at else None,

        "production_bug":
            bool(issue.production_bug)
    }


def create_audit_log(db, issue_id, user_id, action, details=None):
    log = AuditLog(
        issue_id=issue_id,
        user_id=user_id,
        action=action,
        details=details
    )
    db.add(log)
    return log


def webhook_issue_stage(issue):
    # The database uses IN_REVIEW for the QA verification stage.
    return "QA_VERIFICATION" if issue.status == IssueStatus.IN_REVIEW else (issue.status.value if issue.status else None)


def sprint_to_dict(sprint):
    return {
        "id": sprint.id,
        "name": sprint.name,
        "goal": sprint.goal,
        "status": sprint.status.value if sprint.status else None,
        "created_at": sprint.created_at.isoformat() if sprint.created_at else None
    }


# ==========================================================
# PAGE ROUTES
# ==========================================================

@app.route("/")
def home():
    return jsonify({
        "message": "BugFlow backend is running!",
        "status": "success"
    })


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/user-dashboard")
def user_dashboard():
    return render_template("user_dashboard.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    # Page-level guard: bounce non-admins away from the HTML
    # page itself, not just the API calls it makes.
    if session.get("role") != "admin":
        return render_template("login.html")

    return render_template("admin_dashboard.html")


@app.route("/report-issue")
def report_issue_page():
    return render_template("issue_form.html")


@app.route("/my-issues")
def my_issues_page():
    return render_template("my_issues.html")


@app.route("/sprints")
@login_required
def sprints_page():
    return render_template("sprints.html")


@app.route("/reports")
@admin_required
def reports_page():
    return render_template("reports.html")


# ==========================================================
# DATABASE TEST
# ==========================================================

@app.route("/api/test")
def test_database():

    db = SessionLocal()

    try:

        db.execute(text("SELECT 1"))

        return jsonify({
            "message": "Backend and PostgreSQL are connected!"
        }), 200

    except Exception as e:

        return jsonify({
            "message": "Database connection failed",
            "error": str(e)
        }), 500

    finally:

        db.close()


# ==========================================================
# REGISTER USER
# ==========================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:

        return jsonify({
            "message": "No data received"
        }), 400


    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")


    if not name or not email or not password:

        return jsonify({
            "message": "Name, email and password are required"
        }), 400


    role = str(role).lower().strip()

    email = str(email).lower().strip()

    name = str(name).strip()


    if role not in ["user", "admin"]:

        return jsonify({
            "message": "Invalid role. Use user or admin."
        }), 400


    db = SessionLocal()


    try:

        existing_user = db.query(User).filter(
            User.email == email
        ).first()


        if existing_user:

            return jsonify({
                "message": "Email already registered"
            }), 409


        password_hash = generate_password_hash(password)


        new_user = User(

            name=name,

            email=email,

            password_hash=password_hash,

            role=role

        )


        db.add(new_user)

        db.commit()

        db.refresh(new_user)


        return jsonify({

            "message": "Registration successful",

            "user": {

                "id": new_user.id,

                "name": new_user.name,

                "email": new_user.email,

                "role": new_user.role

            }

        }), 201


    except Exception as e:

        db.rollback()

        return jsonify({

            "message": "Registration failed",

            "error": str(e)

        }), 500


    finally:

        db.close()


# ==========================================================
# LOGIN USER
# ==========================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()


    if not data:

        return jsonify({
            "message": "No data received"
        }), 400


    email = data.get("email")
    password = data.get("password")


    if not email or not password:

        return jsonify({
            "message": "Email and password are required"
        }), 400


    email = str(email).lower().strip()


    db = SessionLocal()


    try:

        user = db.query(User).filter(
            User.email == email
        ).first()


        if not user:

            return jsonify({
                "message": "Invalid email or password"
            }), 401


        if not check_password_hash(
            user.password_hash,
            password
        ):

            return jsonify({
                "message": "Invalid email or password"
            }), 401


        # ----------------------------------------------
        # LOG THE USER IN SERVER-SIDE
        # ----------------------------------------------

        session["user_id"] = user.id
        session["role"] = user.role
        session["name"] = user.name


        return jsonify({

            "message": "Login successful",

            "user": {

                "id": user.id,

                "name": user.name,

                "email": user.email,

                "role": user.role

            }

        }), 200


    except Exception as e:

        return jsonify({

            "message": "Login failed",

            "error": str(e)

        }), 500


    finally:

        db.close()


# ==========================================================
# LOGOUT USER
# ==========================================================

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({
        "message": "Logged out successfully"
    }), 200


# ==========================================================
# CREATE ISSUE
# ==========================================================

@app.route("/api/issues", methods=["POST"])
@login_required
def create_issue():

    data = request.get_json()


    if not data:

        return jsonify({
            "message": "No data received"
        }), 400


    issue_type = data.get("issue_type")
    title = data.get("title")
    description = data.get("description")
    reproduction_steps = data.get("reproduction_steps")
    severity = data.get("severity")
    priority = data.get("priority")
    affected_module = data.get("affected_module")
    environment = data.get("environment")
    project_key = data.get("project_key")

    # Reporter is now taken from the logged-in session,
    # not trusted from the request body.
    reporter_id = session["user_id"]


    required = {

        "issue_type": issue_type,

        "title": title,

        "description": description,

        "severity": severity,

        "priority": priority,

        "project_key": project_key

    }


    for field, value in required.items():

        if value is None or value == "":

            return jsonify({

                "message":
                    f"{field} is required"

            }), 400


    db = SessionLocal()


    try:

        reporter = db.query(User).filter(
            User.id == reporter_id
        ).first()


        if not reporter:

            return jsonify({

                "message":
                    "Reporter not found"

            }), 404


        try:

            issue_type_enum = IssueType(
                str(issue_type).upper()
            )

            severity_enum = Severity(
                str(severity).upper()
            )

            priority_enum = Priority(
                str(priority).upper()
            )

        except ValueError as e:

            return jsonify({

                "message":
                    "Invalid issue type, severity or priority",

                "error":
                    str(e)

            }), 400


        project_key = str(
            project_key
        ).strip().upper()


        issue_count = db.query(Issue).count() + 1

        issue_key = f"{project_key}-{issue_count}"


        new_issue = Issue(

            issue_key=issue_key,

            issue_type=issue_type_enum,

            title=str(title).strip(),

            description=str(
                description
            ).strip(),

            reproduction_steps=
                reproduction_steps,

            severity=severity_enum,

            priority=priority_enum,

            status=IssueStatus.REPORTED,

            affected_module=
                affected_module,

            environment=
                environment,

            project_key=
                project_key,

            reporter_id=
                reporter_id

        )


        db.add(new_issue)

        db.commit()

        db.refresh(new_issue)


        return jsonify({

            "message":
                "Issue created successfully",

            "issue":
                issue_to_dict(new_issue)

        }), 201


    except Exception as e:

        db.rollback()

        traceback.print_exc()

        return jsonify({

            "message":
                "Failed to create issue",

            "error":
                str(e)

        }), 500


    finally:

        db.close()


# ==========================================================
# GET ALL ISSUES - PAGINATED
# ==========================================================

@app.route("/api/issues", methods=["GET"])
@login_required
def get_issues():

    db = SessionLocal()

    try:
        try:
            skip = int(request.args.get("skip", 0))
            limit = int(request.args.get("limit", 20))
        except (TypeError, ValueError):
            return jsonify({
                "message": "skip and limit must be integers"
            }), 400

        if skip < 0:
            return jsonify({
                "message": "skip must be greater than or equal to 0"
            }), 400

        if limit < 20 or limit > 50:
            return jsonify({
                "message": "limit must be between 20 and 50"
            }), 400

        total = db.query(Issue).count()

        issues = (
            db.query(Issue)
            .order_by(Issue.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        returned_count = len(issues)

        return jsonify({
            "issues": [
                issue_to_dict(issue)
                for issue in issues
            ],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "returned": returned_count,
                "total": total,
                "has_next": (skip + returned_count) < total,
                "has_previous": skip > 0
            }
        }), 200

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({
            "message": "Failed to fetch issues",
            "error": str(e)
        }), 500

    finally:
        db.close()


# ==========================================================
# GET SINGLE ISSUE
# ==========================================================

@app.route(
    "/api/issues/<int:issue_id>",
    methods=["GET"]
)
@login_required
def get_issue(issue_id):

    db = SessionLocal()


    try:

        issue = db.query(Issue).filter(
            Issue.id == issue_id
        ).first()


        if not issue:

            return jsonify({

                "message":
                    "Issue not found"

            }), 404


        return jsonify(
            issue_to_dict(issue)
        ), 200


    except Exception as e:

        return jsonify({

            "message":
                "Failed to fetch issue",

            "error":
                str(e)

        }), 500


    finally:

        db.close()


# ==========================================================
# UPDATE ISSUE STATUS   (ADMIN ONLY)
# ==========================================================

@app.route(
    "/api/issues/<int:issue_id>/status",
    methods=["PUT"]
)
@admin_required
def update_issue_status(issue_id):

    data = request.get_json()


    if not data:

        return jsonify({

            "message":
                "No data received"

        }), 400


    new_status = data.get("status")


    if not new_status:

        return jsonify({

            "message":
                "Status is required"

        }), 400


    db = SessionLocal()


    try:

        issue = db.query(Issue).filter(
            Issue.id == issue_id
        ).first()


        if not issue:

            return jsonify({

                "message":
                    "Issue not found"

            }), 404


        try:

            issue.status = IssueStatus(
                str(new_status).upper()
            )

        except ValueError:

            return jsonify({

                "message":
                    "Invalid status",

                "allowed_statuses": [

                    status.value

                    for status in IssueStatus

                ]

            }), 400


        db.commit()

        db.refresh(issue)


        return jsonify({

            "message":
                "Issue status updated successfully",

            "issue":
                issue_to_dict(issue)

        }), 200


    except Exception as e:

        db.rollback()

        return jsonify({

            "message":
                "Failed to update issue status",

            "error":
                str(e)

        }), 500


    finally:

        db.close()


# ==========================================================
# UPDATE ISSUE PRIORITY   (ADMIN ONLY)
# ==========================================================

@app.route(
    "/api/issues/<int:issue_id>/priority",
    methods=["PUT"]
)
@admin_required
def update_issue_priority(issue_id):

    data = request.get_json()


    if not data:

        return jsonify({

            "message":
                "No data received"

        }), 400


    new_priority = data.get("priority")


    if not new_priority:

        return jsonify({

            "message":
                "Priority is required"

        }), 400


    db = SessionLocal()


    try:

        issue = db.query(Issue).filter(
            Issue.id == issue_id
        ).first()


        if not issue:

            return jsonify({

                "message":
                    "Issue not found"

            }), 404


        try:

            issue.priority = Priority(
                str(new_priority).upper()
            )

        except ValueError:

            return jsonify({

                "message":
                    "Invalid priority"

            }), 400


        db.commit()

        db.refresh(issue)


        return jsonify({

            "message":
                "Priority updated successfully",

            "issue":
                issue_to_dict(issue)

        }), 200


    except Exception as e:

        db.rollback()

        return jsonify({

            "message":
                "Failed to update priority",

            "error":
                str(e)

        }), 500


    finally:

        db.close()


# ==========================================================
# ASSIGN ISSUE TO SPRINT   (ADMIN ONLY)
# ==========================================================

@app.route(
    "/api/issues/<int:issue_id>/sprint",
    methods=["PUT"]
)
@admin_required
def assign_issue_to_sprint(issue_id):

    data = request.get_json()

    if not data:
        return jsonify({"message": "No data received"}), 400

    sprint_id = data.get("sprint_id")

    db = SessionLocal()

    try:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()

        if not issue:
            return jsonify({"message": "Issue not found"}), 404

        if sprint_id:
            sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
            if not sprint:
                return jsonify({"message": "Sprint not found"}), 404

        issue.sprint_id = sprint_id

        db.commit()
        db.refresh(issue)

        return jsonify({
            "message": "Issue assigned to sprint",
            "issue": issue_to_dict(issue)
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            "message": "Failed to assign issue to sprint",
            "error": str(e)
        }), 500

    finally:
        db.close()


# ==========================================================
# DELETE ISSUE   (ADMIN ONLY)
# ==========================================================

@app.route(
    "/api/issues/<int:issue_id>",
    methods=["DELETE"]
)
@admin_required
def delete_issue(issue_id):

    db = SessionLocal()


    try:

        issue = db.query(Issue).filter(
            Issue.id == issue_id
        ).first()


        if not issue:

            return jsonify({

                "message":
                    "Issue not found"

            }), 404


        db.delete(issue)

        db.commit()


        return jsonify({

            "message":
                "Issue deleted successfully"

        }), 200


    except Exception as e:

        db.rollback()

        return jsonify({

            "message":
                "Failed to delete issue",

            "error":
                str(e)

        }), 500


    finally:

        db.close()


# ==========================================================
# CREATE SPRINT   (ADMIN ONLY)
# ==========================================================

@app.route("/api/sprints", methods=["POST"])
@admin_required
def create_sprint():

    data = request.get_json()

    if not data:
        return jsonify({"message": "No data received"}), 400

    name = data.get("name")
    goal = data.get("goal", "")

    if not name:
        return jsonify({"message": "Sprint name is required"}), 400

    db = SessionLocal()

    try:
        new_sprint = Sprint(
            name=str(name).strip(),
            goal=str(goal).strip(),
            status=SprintStatus.PLANNING
        )

        db.add(new_sprint)
        db.commit()
        db.refresh(new_sprint)

        return jsonify({
            "message": "Sprint created successfully",
            "sprint": sprint_to_dict(new_sprint)
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({
            "message": "Failed to create sprint",
            "error": str(e)
        }), 500

    finally:
        db.close()


# ==========================================================
# GET ALL SPRINTS
# ==========================================================

@app.route("/api/sprints", methods=["GET"])
@login_required
def get_sprints():

    db = SessionLocal()

    try:
        sprints = db.query(Sprint).order_by(Sprint.id.desc()).all()

        return jsonify({
            "sprints": [sprint_to_dict(s) for s in sprints]
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Failed to fetch sprints",
            "error": str(e)
        }), 500

    finally:
        db.close()


# ==========================================================
# UPDATE SPRINT STATUS   (ADMIN ONLY)
# ==========================================================

@app.route("/api/sprints/<int:sprint_id>/status", methods=["PUT"])
@admin_required
def update_sprint_status(sprint_id):

    data = request.get_json()

    if not data:
        return jsonify({"message": "No data received"}), 400

    new_status = data.get("status")

    if not new_status:
        return jsonify({"message": "Status is required"}), 400

    db = SessionLocal()

    try:
        sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()

        if not sprint:
            return jsonify({"message": "Sprint not found"}), 404

        try:
            sprint.status = SprintStatus(str(new_status).upper())
        except ValueError:
            return jsonify({
                "message": "Invalid status",
                "allowed_statuses": [s.value for s in SprintStatus]
            }), 400

        db.commit()
        db.refresh(sprint)

        return jsonify({
            "message": "Sprint status updated",
            "sprint": sprint_to_dict(sprint)
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({
            "message": "Failed to update sprint",
            "error": str(e)
        }), 500

    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - QUALITY SCORECARD
# ==========================================================

@app.route("/api/v1/metrics", methods=["GET"])
@login_required
def quality_metrics():
    db = SessionLocal()
    try:
        issues = db.query(Issue).all()
        total = len(issues)
        resolved_count = sum(
            1 for issue in issues
            if issue.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]
        )

        fix_rate = (resolved_count / total * 100) if total else 0.0

        mttr_values = []
        for issue in issues:
            if issue.resolved_at and issue.created_at:
                delta = issue.resolved_at - issue.created_at
                mttr_values.append(delta.total_seconds() / 3600)

        mttr_hours = (
            sum(mttr_values) / len(mttr_values)
            if mttr_values else 0.0
        )

        production_bugs = sum(
            1 for issue in issues if bool(issue.production_bug)
        )
        defect_leakage_rate = (
            production_bugs / total * 100
            if total else 0.0
        )

        open_critical = sum(
            1 for issue in issues
            if issue.severity == Severity.CRITICAL
            and issue.status not in [IssueStatus.RESOLVED, IssueStatus.CLOSED]
        )
        backlog_health_score = max(0, 100 - (open_critical * 10))

        return jsonify({
            "total_issues": total,
            "resolved_or_closed": resolved_count,
            "fix_rate": round(fix_rate, 2),
            "mttr_hours": round(mttr_hours, 2),
            "production_bugs": production_bugs,
            "defect_leakage_rate": round(defect_leakage_rate, 2),
            "open_critical_bugs": open_critical,
            "backlog_health_score": backlog_health_score,
            "backlog_health_status": (
                "RELEASE_READY"
                if backlog_health_score >= 90
                else "NEEDS_ATTENTION"
            )
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Failed to calculate metrics", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - DEFECT TREND (14 DAYS)
# ==========================================================

@app.route("/api/v1/analytics/defect-trend", methods=["GET"])
@login_required
def defect_trend():
    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        dates = [today - timedelta(days=i) for i in range(13, -1, -1)]
        issues = db.query(Issue).all()

        new_counts = []
        resolved_counts = []

        for day in dates:
            new_counts.append(sum(
                1 for issue in issues
                if issue.created_at and issue.created_at.date() == day
            ))
            resolved_counts.append(sum(
                1 for issue in issues
                if issue.resolved_at and issue.resolved_at.date() == day
            ))

        return jsonify({
            "days": [d.isoformat() for d in dates],
            "new_bugs": new_counts,
            "resolved_bugs": resolved_counts
        }), 200
    except Exception as e:
        return jsonify({"message": "Failed to generate defect trend", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - SEVERITY ANALYTICS
# ==========================================================

@app.route("/api/v1/analytics/severity", methods=["GET"])
@login_required
def severity_analytics():
    db = SessionLocal()
    try:
        counts = {}
        for severity in Severity:
            counts[severity.value] = db.query(Issue).filter(
                Issue.severity == severity
            ).count()

        return jsonify(counts), 200
    except Exception as e:
        return jsonify({"message": "Failed to generate severity analytics", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - WORKFLOW PIPELINE
# ==========================================================

@app.route("/api/v1/analytics/workflow", methods=["GET"])
@login_required
def workflow_analytics():
    db = SessionLocal()
    try:
        # The current PostgreSQL enum stores the QA verification
        # stage as IN_REVIEW. BugFlow displays it as QA_VERIFICATION.
        stages = {
            "REPORTED": IssueStatus.REPORTED,
            "QA_VERIFICATION": IssueStatus.IN_REVIEW,
            "RESOLVED": IssueStatus.RESOLVED,
            "CLOSED": IssueStatus.CLOSED
        }
        result = {
            label: db.query(Issue).filter(Issue.status == status).count()
            for label, status in stages.items()
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Failed to generate workflow analytics", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - PLOTLY DATA / FIGURES
# ==========================================================

@app.route("/api/v1/analytics/plotly", methods=["GET"])
@login_required
def plotly_analytics():
    db = SessionLocal()
    try:
        import plotly.graph_objects as go

        issues = db.query(Issue).all()
        today = datetime.utcnow().date()
        dates = [today - timedelta(days=i) for i in range(13, -1, -1)]
        new_counts = []
        resolved_counts = []

        for day in dates:
            new_counts.append(sum(
                1 for issue in issues
                if issue.created_at and issue.created_at.date() == day
            ))
            resolved_counts.append(sum(
                1 for issue in issues
                if issue.resolved_at and issue.resolved_at.date() == day
            ))

        trend = go.Figure()
        trend.add_trace(go.Scatter(
            x=[d.isoformat() for d in dates],
            y=new_counts,
            mode="lines+markers",
            name="New Bugs"
        ))
        trend.add_trace(go.Scatter(
            x=[d.isoformat() for d in dates],
            y=resolved_counts,
            mode="lines+markers",
            name="Resolved Bugs"
        ))
        trend.update_layout(title="Defect Trend - Last 14 Days")

        severity_labels = [s.value for s in Severity]
        severity_values = [
            sum(1 for issue in issues if issue.severity == s)
            for s in Severity
        ]
        donut = go.Figure(data=[go.Pie(
            labels=severity_labels,
            values=severity_values,
            hole=0.55
        )])
        donut.update_layout(title="Severity Distribution")

        stage_labels = ["REPORTED", "QA_VERIFICATION", "RESOLVED", "CLOSED"]
        stage_statuses = [
            IssueStatus.REPORTED,
            IssueStatus.IN_REVIEW,
            IssueStatus.RESOLVED,
            IssueStatus.CLOSED
        ]
        stage_values = [
            sum(1 for issue in issues if issue.status == status)
            for status in stage_statuses
        ]
        pipeline = go.Figure(data=[go.Bar(
            x=stage_labels,
            y=stage_values
        )])
        pipeline.update_layout(title="Workflow Pipeline")

        return jsonify({
            "defect_trend": trend.to_plotly_json(),
            "severity_donut": donut.to_plotly_json(),
            "workflow_pipeline": pipeline.to_plotly_json()
        }), 200
    except ImportError:
        return jsonify({"message": "Plotly is not installed. Run: pip install plotly"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Failed to generate Plotly analytics", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - GIT WEBHOOK
# ==========================================================

@app.route("/api/v1/webhooks/git", methods=["POST"])
def git_webhook():
    data = request.get_json(silent=True) or {}

    commit_message = (
        data.get("commit_message")
        or data.get("message")
        or ((data.get("head_commit") or {}).get("message"))
        or ""
    )
    commit_hash = (
        data.get("commit_hash")
        or data.get("commit")
        or data.get("after")
        or ((data.get("head_commit") or {}).get("id"))
        or "unknown"
    )

    matches = re.findall(
        r"\b(?:fixes|closes|resolves)\s+#(\d+)\b",
        str(commit_message),
        flags=re.IGNORECASE
    )

    if not matches:
        return jsonify({
            "message": "No issue references found in commit message",
            "commit_message": commit_message,
            "updated_issues": []
        }), 200

    db = SessionLocal()
    updated = []
    not_found = []

    try:
        for issue_id_text in matches:
            issue_id = int(issue_id_text)
            issue = db.query(Issue).filter(Issue.id == issue_id).first()

            if not issue:
                not_found.append(issue_id)
                continue

            old_status = issue.status.value if issue.status else None

            # Current PostgreSQL enum uses IN_REVIEW for the
            # QA verification stage shown by BugFlow.
            issue.status = IssueStatus.IN_REVIEW

            create_audit_log(
                db,
                issue.id,
                issue.reporter_id,
                "GIT_WEBHOOK_AUTO_TRANSITION",
                f"Auto-transitioned by Git commit #{str(commit_hash)[:9]}: {old_status} -> QA_VERIFICATION"
            )

            updated.append({
                "id": issue.id,
                "issue_key": issue.issue_key,
                "old_status": old_status,
                "new_status": "QA_VERIFICATION",
                "stored_status": IssueStatus.IN_REVIEW.value
            })

        db.commit()

        return jsonify({
            "message": "Git webhook processed successfully",
            "commit_hash": commit_hash,
            "updated_issues": updated,
            "not_found": not_found
        }), 200
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"message": "Git webhook processing failed", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 4 - DEVELOPER WORKLOAD MATRIX
# ==========================================================

@app.route("/api/v1/analytics/developer-workload", methods=["GET"])
@login_required
def developer_workload():

    db = SessionLocal()

    try:
        users = db.query(User).order_by(User.id.asc()).all()
        issues = db.query(Issue).all()

        # The current PostgreSQL enum does not contain IN_PROGRESS.
        # IN_REVIEW is the persisted QA/code-review workflow stage.
        active_statuses = {IssueStatus.IN_REVIEW}
        completed_statuses = {
            IssueStatus.RESOLVED,
            IssueStatus.CLOSED
        }

        developers = []

        for user in users:
            assigned = [
                issue for issue in issues
                if issue.assignee_id == user.id
            ]

            active_tasks = sum(
                1 for issue in assigned
                if issue.status in active_statuses
            )

            completed = [
                issue for issue in assigned
                if issue.status in completed_statuses
            ]

            mttr_values = [
                (issue.resolved_at - issue.created_at).total_seconds() / 3600
                for issue in completed
                if issue.resolved_at and issue.created_at
            ]

            average_mttr_hours = (
                sum(mttr_values) / len(mttr_values)
                if mttr_values else 0.0
            )

            developers.append({
                "developer_id": user.id,
                "developer": user.name,
                "team": "BugFlow Engineering",
                "role": user.role,
                "active_tasks": active_tasks,
                "completed_fixes": len(completed),
                "average_mttr_hours": round(
                    average_mttr_hours, 2
                )
            })

        active_counts = [
            developer["active_tasks"]
            for developer in developers
        ]

        if active_counts:
            max_tasks = max(active_counts)
            min_tasks = min(active_counts)
        else:
            max_tasks = 0
            min_tasks = 0

        difference = max_tasks - min_tasks

        if difference <= 2:
            balance_status = "BALANCED"
        elif difference <= 5:
            balance_status = "MODERATE_IMBALANCE"
        else:
            balance_status = "IMBALANCED"

        return jsonify({
            "developers": developers,
            "resource_balance": {
                "max_active_tasks": max_tasks,
                "min_active_tasks": min_tasks,
                "difference": difference,
                "status": balance_status
            }
        }), 200

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({
            "message": "Failed to calculate developer workload",
            "error": str(e)
        }), 500

    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - AUDIT HISTORY
# ==========================================================

@app.route("/api/v1/issues/<int:issue_id>/audit", methods=["GET"])
@login_required
def issue_audit_history(issue_id):
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(
            AuditLog.issue_id == issue_id
        ).order_by(AuditLog.id.desc()).all()

        return jsonify({
            "issue_id": issue_id,
            "audit_logs": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "details": log.details,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]
        }), 200
    except Exception as e:
        return jsonify({"message": "Failed to fetch audit history", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - CSV EXPORT
# ==========================================================

@app.route("/api/v1/export/csv", methods=["GET"])
@login_required
def export_csv():
    db = SessionLocal()
    try:
        issues = db.query(Issue).order_by(Issue.id.asc()).all()
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "ID", "Issue Key", "Type", "Title", "Description",
            "Status", "Severity", "Priority", "Affected Module",
            "Environment", "Project Key", "Reporter ID", "Assignee ID",
            "Sprint ID", "Created At", "Resolved At", "Production Bug"
        ])

        for issue in issues:
            writer.writerow([
                issue.id,
                issue.issue_key,
                issue.issue_type.value if issue.issue_type else "",
                issue.title,
                issue.description,
                issue.status.value if issue.status else "",
                issue.severity.value if issue.severity else "",
                issue.priority.value if issue.priority else "",
                issue.affected_module or "",
                issue.environment or "",
                issue.project_key,
                issue.reporter_id,
                issue.assignee_id or "",
                issue.sprint_id or "",
                issue.created_at.isoformat() if issue.created_at else "",
                issue.resolved_at.isoformat() if issue.resolved_at else "",
                bool(issue.production_bug)
            ])

        response = app.response_class(
            output.getvalue(),
            mimetype="text/csv"
        )
        response.headers["Content-Disposition"] = "attachment; filename=bugflow_bug_registry.csv"
        return response
    except Exception as e:
        return jsonify({"message": "CSV export failed", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# MILESTONE 3 - PDF EXPORT
# ==========================================================

@app.route("/api/v1/export/pdf", methods=["GET"])
@login_required
def export_pdf():
    db = SessionLocal()
    try:
        from fpdf import FPDF

        issues = db.query(Issue).order_by(Issue.id.desc()).all()
        total = len(issues)
        resolved = sum(
            1 for issue in issues
            if issue.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]
        )
        critical_open = sum(
            1 for issue in issues
            if issue.severity == Severity.CRITICAL
            and issue.status not in [IssueStatus.RESOLVED, IssueStatus.CLOSED]
        )
        production_bugs = sum(1 for issue in issues if bool(issue.production_bug))
        fix_rate = resolved / total * 100 if total else 0
        leakage = production_bugs / total * 100 if total else 0
        mttr_values = [
            (issue.resolved_at - issue.created_at).total_seconds() / 3600
            for issue in issues
            if issue.resolved_at and issue.created_at
        ]
        mttr = sum(mttr_values) / len(mttr_values) if mttr_values else 0
        health = max(0, 100 - critical_open * 10)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 18)
        pdf.cell(0, 12, "BugFlow - Quality Scorecard", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 8, f"Generated: {datetime.utcnow().isoformat()} UTC", ln=True)
        pdf.ln(5)

        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 9, "Executive Summary", ln=True)
        pdf.set_font("Arial", size=11)
        summary = [
            f"Total Issues: {total}",
            f"Resolved / Closed: {resolved}",
            f"Fix Rate: {fix_rate:.2f}%",
            f"MTTR: {mttr:.2f} hours",
            f"Production Bugs: {production_bugs}",
            f"Defect Leakage Rate: {leakage:.2f}%",
            f"Open Critical Bugs: {critical_open}",
            f"Backlog Health Score: {health}/100"
        ]
        for line in summary:
            pdf.cell(0, 7, line, ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 9, "Recent Critical Bugs", ln=True)
        pdf.set_font("Arial", size=10)

        critical = [
            issue for issue in issues
            if issue.severity == Severity.CRITICAL
        ][:10]

        if not critical:
            pdf.cell(0, 7, "No critical bugs found.", ln=True)
        else:
            for issue in critical:
                title = str(issue.title).replace("\n", " ")[:90]
                pdf.multi_cell(
                    0,
                    7,
                    f"{issue.issue_key} | {issue.status.value} | {title}"
                )

        data = bytes(pdf.output())
        response = app.response_class(data, mimetype="application/pdf")
        response.headers["Content-Disposition"] = "attachment; filename=bugflow_quality_report.pdf"
        return response
    except ImportError:
        return jsonify({"message": "fpdf2 is not installed. Run: pip install fpdf2"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "PDF export failed", "error": str(e)}), 500
    finally:
        db.close()


# ==========================================================
# START SERVER
# ==========================================================


# ==========================================================
# MILESTONE 4 - HEALTH & API DOCUMENTATION
# ==========================================================

@app.route('/health', methods=['GET'])
def health_check():
    db = SessionLocal()
    try:
        db.execute(text('SELECT 1'))
        return jsonify({'status':'healthy','service':'BugFlow','database':'PostgreSQL','database_status':'connected'}), 200
    except Exception as e:
        return jsonify({'status':'unhealthy','service':'BugFlow','database_status':'disconnected','error':str(e)}), 503
    finally:
        db.close()

@app.route('/docs', methods=['GET'])
def api_docs():
    return """<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>BugFlow API Documentation</title><style>body{font-family:Arial,sans-serif;background:#0b0b14;color:white;padding:40px}.card{max-width:950px;margin:auto;background:#151523;border:1px solid #29293b;border-radius:12px;padding:30px}h1{color:#9b7cff}h2{margin-top:28px}.endpoint{background:#0b0b14;border:1px solid #29293b;padding:12px;margin:8px 0;border-radius:7px}.method{color:#69e6a5;font-weight:bold}code{color:#b8aaff}</style></head><body><div class='card'><h1>BugFlow API Documentation</h1><p>Software Issue Tracking &amp; Resolution Platform</p><h2>System</h2><div class='endpoint'><span class='method'>GET</span> <code>/health</code> — System and database health check</div><h2>Authentication</h2><div class='endpoint'><span class='method'>POST</span> <code>/api/register</code> — Register a user</div><div class='endpoint'><span class='method'>POST</span> <code>/api/login</code> — Authenticate a user</div><h2>Issues</h2><div class='endpoint'><span class='method'>GET</span> <code>/api/issues?skip=0&amp;limit=20</code> — Paginated issue list (20–50 records)</div><div class='endpoint'><span class='method'>POST</span> <code>/api/issues</code> — Create an issue</div><h2>Analytics</h2><div class='endpoint'><span class='method'>GET</span> <code>/api/v1/metrics</code> — Quality scorecard metrics</div><div class='endpoint'><span class='method'>GET</span> <code>/api/v1/analytics/defect-trend</code> — 14-day defect trend</div><div class='endpoint'><span class='method'>GET</span> <code>/api/v1/analytics/severity</code> — Severity distribution</div><div class='endpoint'><span class='method'>GET</span> <code>/api/v1/analytics/workflow</code> — Workflow pipeline</div><div class='endpoint'><span class='method'>GET</span> <code>/api/v1/analytics/developer-workload</code> — Developer workload matrix</div><h2>Git Integration</h2><div class='endpoint'><span class='method'>POST</span> <code>/api/v1/webhooks/git</code> — Process Git commit webhook</div><h2>Exports</h2><div class='endpoint'><span class='method'>GET</span> <code>/api/v1/export/pdf</code> — Export PDF report</div><div class='endpoint'><span class='method'>GET</span> <code>/api/v1/export/csv</code> — Export CSV report</div><h2>Module 4 Performance</h2><p>Connection pool: <strong>20 + 10 overflow = 30</strong></p><p>Measured authenticated API response: <strong>26.99 ms</strong></p><p>Target response time: <strong>&lt; 300 ms</strong></p></div></body></html>"""

@app.route('/redoc', methods=['GET'])
def redoc_docs():
    return """<!DOCTYPE html><html><head><title>BugFlow ReDoc</title><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><script src='https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js'></script></head><body><redoc spec-url='/openapi.json'></redoc></body></html>"""

@app.route('/openapi.json', methods=['GET'])
def openapi_json():
    return jsonify({'openapi':'3.0.0','info':{'title':'BugFlow API','version':'1.0.0','description':'Software Issue Tracking & Resolution Platform'},'paths':{'/health':{'get':{'summary':'Health check'}},'/api/issues':{'get':{'summary':'Get paginated issues'},'post':{'summary':'Create an issue'}},'/api/v1/metrics':{'get':{'summary':'Quality scorecard metrics'}},'/api/v1/analytics/developer-workload':{'get':{'summary':'Developer workload matrix'}},'/api/v1/webhooks/git':{'post':{'summary':'Git webhook processor'}},'/api/v1/export/pdf':{'get':{'summary':'Export PDF report'}},'/api/v1/export/csv':{'get':{'summary':'Export CSV report'}}}})

if __name__ == "__main__":

    print("======================================")
    print("      BUGFLOW SERVER STARTING")
    print("======================================")
    print("Server: http://127.0.0.1:8000")
    print("Register: http://127.0.0.1:8000/register")
    print("Login: http://127.0.0.1:8000/login")
    print("Sprints: http://127.0.0.1:8000/sprints")
    print("DB Test: http://127.0.0.1:8000/api/test")
    print("======================================")

    app.run(

        host="127.0.0.1",

        port=8000,

        debug=True

    )