def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/videos/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "videos route is working"}
