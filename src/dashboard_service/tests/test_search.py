from .conftest import create_test_video


def test_search_empty_database(client):
    """Test search when database is empty."""
    response = client.get("/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test"
    assert data["results"] == []


def test_search_single_match(client, test_db):
    """Test search with a single matching video."""
    video = create_test_video(test_db, title="Python Tutorial")
    
    response = client.get("/search?q=python")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "python"
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == video.id
    assert data["results"][0]["title"] == "Python Tutorial"


def test_search_multiple_matches(client, test_db):
    """Test search with multiple matching videos."""
    video1 = create_test_video(test_db, title="Python Basics", uploader_id=1)
    video2 = create_test_video(test_db, title="Advanced Python", uploader_id=2)
    video3 = create_test_video(test_db, title="JavaScript Tutorial", uploader_id=3)
    
    response = client.get("/search?q=python")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    result_ids = {r["id"] for r in data["results"]}
    assert video1.id in result_ids
    assert video2.id in result_ids
    assert video3.id not in result_ids


def test_search_case_insensitive(client, test_db):
    """Test that search is case insensitive."""
    video = create_test_video(test_db, title="Python Tutorial")
    
    response = client.get("/search?q=PYTHON")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1


def test_search_partial_match(client, test_db):
    """Test search with partial title matches."""
    video = create_test_video(test_db, title="Introduction to FastAPI")
    
    response = client.get("/search?q=fast")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1


def test_search_with_user_id_records_history(client, test_db):
    """Test that providing user_id records the search in history."""
    video = create_test_video(test_db, title="Test Video")
    user_id = "user123"
    
    response = client.get(f"/search?q=test&user_id={user_id}")
    assert response.status_code == 200
    
    # Verify search was recorded
    response = client.get(f"/search/history?user_id={user_id}")
    data = response.json()
    assert len(data["history"]) == 1
    assert data["history"][0]["query"] == "test"


def test_search_missing_query_param(client):
    """Test search with missing required query parameter."""
    response = client.get("/search")
    assert response.status_code == 422


def test_search_empty_query(client):
    """Test search with empty query string."""
    response = client.get("/search?q=")
    assert response.status_code == 422


def test_search_response_structure(client, test_db):
    """Test that search response has correct structure."""
    video = create_test_video(test_db, title="Test Video", uploader_id=5)
    
    response = client.get("/search?q=test")
    data = response.json()
    
    assert "query" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    
    if data["results"]:
        result = data["results"][0]
        required_fields = {
            "id", "title", "description", "category", "tags",
            "thumbnail_url", "uploader_id", "views", "likes",
            "duration_seconds", "created_at"
        }
        assert required_fields.issubset(result.keys())
