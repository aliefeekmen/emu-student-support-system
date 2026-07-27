import os

import pytest
from fastapi.testclient import TestClient


os.environ.setdefault(
    "SESSION_SECRET",
    "test-only-session-secret",
)

from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_session_cookies():
    client.cookies.clear()
    yield
    client.cookies.clear()


def login_as_staff():
    response = client.post(
        "/login",
        data={
            "email": "staff@demo.local",
            "password": "Staff123!",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


def login_as_student():
    response = client.post(
        "/login",
        data={
            "email": "student@demo.local",
            "password": "Student123!",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_login_page():
    response = client.get("/login")

    assert response.status_code == 200
    assert "Sign in to your account" in response.text


def test_protected_endpoint_requires_login():
    response = client.get("/categories")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required."
    }


def test_statistics_endpoint():
    login_as_staff()

    response = client.get("/stats")
    data = response.json()

    assert response.status_code == 200
    assert data["knowledge_entries"] == 769
    assert data["categories"] == 31
    assert data["languages"] == 2


def test_categories_endpoint():
    login_as_student()

    response = client.get("/categories")
    categories = response.json()

    assert response.status_code == 200
    assert len(categories) == 31


def test_knowledge_search():
    login_as_staff()

    response = client.get(
        "/knowledge",
        params={
            "language": "tr",
            "search": "portal",
            "limit": 5,
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["total"] > 0
    assert data["limit"] == 5
    assert len(data["items"]) <= 5

    for item in data["items"]:
        assert item["language"] == "tr"


def test_get_existing_knowledge_entry():
    login_as_staff()

    response = client.get("/knowledge/7136")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 7136
    assert data["language"] == "tr"


def test_get_missing_knowledge_entry():
    login_as_staff()

    response = client.get("/knowledge/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Knowledge entry not found."
    }


def test_expert_dashboard_page():
    login_as_staff()

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Student Q&A Center" in response.text
    assert "Expert Panel" in response.text
    assert "Demo Staff" in response.text


def test_student_dashboard_page():
    login_as_student()

    response = client.get("/student-dashboard")

    assert response.status_code == 200
    assert "Student Q&A Center" in response.text
    assert "Ask New Question" in response.text
    assert "Demo Student" in response.text


def test_current_user_endpoint():
    login_as_staff()

    response = client.get("/me")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 2
    assert data["role"] == "staff"


def test_dashboard_stylesheet():
    response = client.get(
        "/static/css/dashboard.css"
    )

    assert response.status_code == 200
    assert ".app-shell" in response.text
    assert ".login-layout" in response.text

def login_as_admin():
    return client.post(
        "/login",
        data={
            "email": "admin@demo.local",
            "password": "Admin123!",
        },
        follow_redirects=False,
    )


def test_admin_dashboard_page():
    login_as_admin()

    response = client.get("/admin-dashboard")

    assert response.status_code == 200


def test_admin_overview_endpoint():
    login_as_admin()

    response = client.get("/admin/overview")
    data = response.json()

    assert response.status_code == 200
    assert data["users"] == 3
    assert data["categories"] == 31
    assert data["knowledge_entries"] == 769


def test_staff_cannot_access_admin_endpoint():
    client.post("/logout")

    client.post(
        "/login",
        data={
            "email": "staff@demo.local",
            "password": "Staff123!",
        },
    )

    response = client.get("/admin/overview")

    assert response.status_code == 403


def test_student_redirected_from_expert_dashboard():
    client.post("/logout")

    client.post(
        "/login",
        data={
            "email": "student@demo.local",
            "password": "Student123!",
        },
    )

    response = client.get(
        "/dashboard",
        follow_redirects=False,
    )

    assert response.status_code in (302, 303, 307)
    assert response.headers["location"] == "/student-dashboard"