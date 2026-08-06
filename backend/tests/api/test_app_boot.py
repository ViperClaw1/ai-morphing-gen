from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_expected_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert paths >= {
        "/projects",
        "/projects/{project_id}",
        "/projects/{project_id}/assets",
        "/jobs/{job_id}",
        "/projects/{project_id}/preview",
        "/projects/{project_id}/render",
        "/checkout",
        "/payments/webhook",
        "/settings/public",
    }


def test_public_settings_returns_real_config():
    response = client.get("/settings/public")
    assert response.status_code == 200
    assert response.json() == {
        "preview_enabled": True,
        "preview_limit_per_project": 3,
        "preview_ttl_hours": 3,
    }


def test_stub_route_returns_501_in_api_convention_shape():
    response = client.get("/jobs/abc123")
    assert response.status_code == 501
    assert response.json().keys() == {"error", "code"}
    assert response.json()["code"] == "NOT_IMPLEMENTED"


def test_request_id_is_echoed_back():
    response = client.get("/settings/public", headers={"X-Request-Id": "test-123"})
    assert response.headers["x-request-id"] == "test-123"
