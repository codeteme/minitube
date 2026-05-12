from .conftest import create_test_search_history


def test_search_history_empty(client):
    """Test search history for user with no searches."""
    response = client.get("/search/history?user_id=user123")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user123"
    assert data["history"] == []


def test_search_history_single_entry(client, test_db):
    """Test search history with a single entry."""
    create_test_search_history(test_db, user_id="user1", query="python tutorial")
    
    response = client.get("/search/history?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user1"
    assert len(data["history"]) == 1
    assert data["history"][0]["query"] == "python tutorial"


def test_search_history_multiple_entries(client, test_db):
    """Test search history with multiple entries."""
    create_test_search_history(test_db, user_id="user1", query="python")
    create_test_search_history(test_db, user_id="user1", query="javascript")
    create_test_search_history(test_db, user_id="user1", query="fastapi")
    
    response = client.get("/search/history?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 3
    queries = [h["query"] for h in data["history"]]
    assert "python" in queries
    assert "javascript" in queries
    assert "fastapi" in queries


def test_search_history_reverse_chronological_order(client, test_db):
    """Test that search history is returned in reverse chronological order."""
    from datetime import datetime, timezone, timedelta
    from src.dashboard_service.models import SearchHistory
    
    # Create entries with different timestamps
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)
    
    entry1 = SearchHistory(user_id="user1", query="first search", searched_at=base_time)
    entry2 = SearchHistory(user_id="user1", query="second search", searched_at=base_time + timedelta(seconds=1))
    entry3 = SearchHistory(user_id="user1", query="third search", searched_at=base_time + timedelta(seconds=2))
    
    test_db.add_all([entry1, entry2, entry3])
    test_db.commit()
    
    response = client.get("/search/history?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 3
    
    # Most recent should be first
    assert data["history"][0]["query"] == "third search"
    assert data["history"][1]["query"] == "second search"
    assert data["history"][2]["query"] == "first search"


def test_search_history_limit_default(client, test_db):
    """Test that search history respects default limit of 10."""
    for i in range(15):
        create_test_search_history(test_db, user_id="user1", query=f"search {i}")
    
    response = client.get("/search/history?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 10


def test_search_history_limit_custom(client, test_db):
    """Test that search history respects custom limit parameter."""
    for i in range(15):
        create_test_search_history(test_db, user_id="user1", query=f"search {i}")
    
    response = client.get("/search/history?user_id=user1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 5


def test_search_history_limit_max_50(client, test_db):
    """Test that limit parameter is capped at 50."""
    for i in range(60):
        create_test_search_history(test_db, user_id="user1", query=f"search {i}")
    
    response = client.get("/search/history?user_id=user1&limit=100")
    assert response.status_code == 422


def test_search_history_limit_min_1(client, test_db):
    """Test that limit parameter must be at least 1."""
    response = client.get("/search/history?user_id=user1&limit=0")
    assert response.status_code == 422


def test_search_history_missing_user_id(client):
    """Test search history with missing user_id parameter."""
    response = client.get("/search/history")
    assert response.status_code == 422


def test_search_history_user_isolation(client, test_db):
    """Test that search history is isolated per user."""
    create_test_search_history(test_db, user_id="user1", query="user1 search")
    create_test_search_history(test_db, user_id="user2", query="user2 search")
    
    response = client.get("/search/history?user_id=user1")
    data = response.json()
    assert len(data["history"]) == 1
    assert data["history"][0]["query"] == "user1 search"


def test_search_history_response_structure(client, test_db):
    """Test that search history response has correct structure."""
    create_test_search_history(test_db, user_id="user1", query="test")
    
    response = client.get("/search/history?user_id=user1")
    data = response.json()
    
    assert "user_id" in data
    assert "history" in data
    assert isinstance(data["history"], list)
    
    if data["history"]:
        entry = data["history"][0]
        assert "query" in entry
        assert "searched_at" in entry
        assert isinstance(entry["searched_at"], str)
