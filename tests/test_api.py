from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_statistics_endpoint():
    response = client.get("/stats")
    data = response.json()

    assert response.status_code == 200
    assert data["knowledge_entries"] == 769
    assert data["categories"] == 31
    assert data["languages"] == 2


def test_categories_endpoint():
    response = client.get("/categories")
    categories = response.json()

    assert response.status_code == 200
    assert len(categories) == 31


def test_knowledge_search():
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
    response = client.get("/knowledge/7136")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 7136
    assert data["language"] == "tr"


def test_get_missing_knowledge_entry():
    response = client.get("/knowledge/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Knowledge entry not found."
    }