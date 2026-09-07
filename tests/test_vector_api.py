from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_vector_search_rejects_empty_embedding():
    response = client.post(
        "/api/v1/evidence/semantic-search",
        json={"embedding": [], "limit": 5},
    )
    assert response.status_code == 422
