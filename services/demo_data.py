"""Deterministic sample plan used ONLY in clearly labelled demo mode."""
import copy

_DEMO_PLAN = {
    "project_title": "Campus Book Exchange (Sample)",
    "project_summary": "A web marketplace where university students list, find and exchange used textbooks within their campus.",
    "project_category": "Marketplace / Education",
    "problem_statement": "Students overspend on new textbooks each semester while used copies sit unused with seniors.",
    "target_users": ["University students buying books", "Graduating students selling books", "Campus society admins"],
    "objectives": ["Let students list books in under a minute", "Make finding a book by course code easy", "Keep exchanges within a trusted campus community"],
    "requirements": ["Student sign-up with university email", "Book listing with photos and condition", "Search by title, author or course code", "In-app messaging between buyer and seller"],
    "assumptions": ["Payments happen in person, not in the app", "One university campus at launch", "Moderate traffic (under 5,000 users)"],
    "missing_information": ["Whether online payments are needed", "Expected number of campuses"],
    "features": [
        {"name": "Student accounts", "description": "Sign-up and login with university email verification.", "category": "mvp", "priority": "high", "hours": 24},
        {"name": "Book listings", "description": "Create, edit and remove listings with photos and condition.", "category": "mvp", "priority": "high", "hours": 32},
        {"name": "Search & filters", "description": "Search by title, author, course code and price.", "category": "mvp", "priority": "high", "hours": 20},
        {"name": "Messaging", "description": "Simple buyer-seller chat per listing.", "category": "mvp", "priority": "medium", "hours": 28},
        {"name": "Ratings", "description": "Rate exchange partners to build trust.", "category": "future", "priority": "medium", "hours": 16},
        {"name": "Online payments", "description": "Optional secure in-app payments.", "category": "future", "priority": "low", "hours": 40},
    ],
    "technology_stack": [
        {"name": "Flask", "category": "Backend", "reason": "Lightweight Python framework, quick to build and easy to explain."},
        {"name": "SQLite", "category": "Database", "reason": "Zero-setup relational storage, enough for a single campus."},
        {"name": "HTML/CSS/JavaScript", "category": "Frontend", "reason": "No build step; responsive pages work on phones."},
        {"name": "Cloudinary", "category": "Media storage", "reason": "Free tier for book photo uploads and resizing."},
    ],
    "task_estimates": [
        {"name": "Requirements & UI wireframes", "description": "Define screens and user flows.", "hours": 16},
        {"name": "Project setup & database schema", "description": "Repo, Flask app, models for users, books, messages.", "hours": 12},
        {"name": "Authentication", "description": "Email verification, login, password reset.", "hours": 24},
        {"name": "Listings CRUD with photos", "description": "Forms, uploads, listing pages.", "hours": 32},
        {"name": "Search & filters", "description": "Query endpoints and search UI.", "hours": 20},
        {"name": "Messaging", "description": "Per-listing conversations.", "hours": 28},
        {"name": "Testing & bug fixing", "description": "Unit tests and manual QA.", "hours": 20},
        {"name": "Deployment & handover", "description": "Hosting setup and documentation.", "hours": 8},
    ],
    "roadmap": [
        {"sequence": 1, "title": "Planning & design", "description": "Wireframes, schema and scope sign-off.", "priority": "high", "dependencies": []},
        {"sequence": 2, "title": "Core platform", "description": "Setup, authentication and listings.", "priority": "high", "dependencies": ["Planning & design"]},
        {"sequence": 3, "title": "Discovery & communication", "description": "Search, filters and messaging.", "priority": "high", "dependencies": ["Core platform"]},
        {"sequence": 4, "title": "Quality & launch", "description": "Testing, fixes and deployment.", "priority": "medium", "dependencies": ["Discovery & communication"]},
    ],
    "risks": [
        {"description": "Fake or spam accounts reduce trust.", "severity": "medium", "mitigation": "Require university email verification and allow reporting."},
        {"description": "Uploaded images expose personal data.", "severity": "low", "mitigation": "Guide users and strip image metadata on upload."},
        {"description": "Scope creep into payments delays launch.", "severity": "high", "mitigation": "Keep payments in a later phase; launch with in-person exchange."},
    ],
    "confidence": "medium",
}


def get_demo_plan():
    """Return a fresh copy of the fixed sample plan."""
    return copy.deepcopy(_DEMO_PLAN)
