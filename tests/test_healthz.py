"""/healthz: sprawdzenie gotowości dla hostingu (keep-alive, restart po awarii)."""


class TestHealthz:
    def test_returns_ok_when_db_reachable(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}

    def test_returns_json_content_type(self, client):
        response = client.get("/healthz")
        assert response.mimetype == "application/json"
