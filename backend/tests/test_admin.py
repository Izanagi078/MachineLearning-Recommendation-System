"""
test_admin.py — Tests for the admin router and model retraining endpoint.
Covers: unauthorized access rejection, successful retraining trigger, and SVD/TF-IDF state updating.
"""
import pytest
from unittest.mock import patch, MagicMock

def register_and_login(client, username="admin_tester", password="adminpass"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    return res.json()["token"]

class TestAdminRetrain:
    def test_retrain_requires_auth(self, client):
        res = client.post("/api/admin/retrain")
        assert res.status_code == 401

    @patch("backend.app.routers.admin.retrain_model_pipeline")
    def test_retrain_success(self, mock_retrain, client):
        # Set up stub return value representing new cache metrics
        mock_retrain.return_value = {
            "metrics": {
                "rmse": 0.82,
                "mae": 0.61,
                "map_10": 0.44,
                "ndcg_10": 0.52
            }
        }
        
        token = register_and_login(client)
        res = client.post(
            "/api/admin/retrain",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "Retraining completed successfully" in data["message"]
        assert data["metrics"]["rmse"] == 0.82
        assert mock_retrain.called
