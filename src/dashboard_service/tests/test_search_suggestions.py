from .conftest import create_test_video


def test_search_suggestions_empty_database(client):
    """Test search suggestions when database is empty."""
    response = client.get("/search/suggestions?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test"
    assert data["suggestions"] == []


def test_search_suggestions_single_match(client, test_db):
    """Test search suggestions with a single matching video."""
    video = create_test_video(test_db, title="Python Tutorial")
    
    response = client.get("/search/suggestions?q=python")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "python"
    assert len(data["suggestions"]) == 1
    assert data["suggestions"][0] == "Python Tutorial"


def test_search_suggestions_multiple_matches(client, test_db):
    """Test search suggestions returns only titles, not full objects."""
    video1 = create_test_video(test_db, title="Python Basics", uploader_id=1)
    video2 = create_test_video(test_db, title="Advanced Python", uploader_id=2)
    video3 = create_test_video(test_db, title="JavaScript Basics", uploader_id=3)
    
    response = client.get("/search/suggestions?q=python")
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) == 2
    assert "Python Basics" in data["suggestions"]
    assert "Advanced Python" in data["suggestions"]
    assert "JavaScript Basics" not in data["suggestions"]


def test_search_suggestions_limit_10(client, test_db):
    """Test that search suggestions respects 10 video limit."""
    for i in range(15):
        create_test_video(test_db, title=f"Test Video {i}", uploader_id=i)
    
    response = client.get("/search/suggestions?q=test")
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) == 10


def test_search_suggestions_case_insensitive(client, test_db):
    """Test that search suggestions are case insensitive."""
    video = create_test_video(test_db, title="Python Tutorial")
    
    response = client.get("/search/suggestions?q=PYTHON")
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) == 1


def test_search_suggestions_partial_match(client, test_db):
    """Test search suggestions with partial matches."""
    video = create_test_video(test_db, title="Introduction to FastAPI")
    
    response = client.get("/search/suggestions?q=intro")
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) == 1


def test_search_suggestions_missing_query(client):
    """Test search suggestions with missing required query parameter."""
    response = client.get("/search/suggestions")
    assert response.status_code == 422


def test_search_suggestions_empty_query(client):
    """Test search suggestions with empty query string."""
    response = client.get("/search/suggestions?q=")
    assert response.status_code == 422


def test_search_suggestions_response_structure(client, test_db):
    """Test that search suggestions response has correct structure."""
    video1 = create_test_video(test_db, title="Test Video 1")
    video2 = create_test_video(test_db, title="Test Video 2")
    
    response = client.get("/search/suggestions?q=test")
    data = response.json()
    
    assert "query" in data
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    for suggestion in data["suggestions"]:
        assert isinstance(suggestion, str)


def test_search_suggestions_returns_titles_only(client, test_db):
    """Verify that suggestions return only title strings, not video objects."""
    video = create_test_video(test_db, title="Python Course")
    
    response = client.get("/search/suggestions?q=python")
    assert response.status_code == 200
    data = response.json()
    
    # Verify responses are strings, not objects
    assert isinstance(data["suggestions"][0], str)
    assert data["suggestions"][0] == "Python Course"
