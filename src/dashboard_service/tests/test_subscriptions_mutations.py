from .conftest import create_test_subscription
from unittest.mock import AsyncMock, patch


def test_list_subscriptions_empty(client):
    response = client.get("/subscriptions?user_id=user1")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user1"
    assert body["channel_user_ids"] == []
    assert body["count"] == 0


def test_subscribe_and_list(client):
    with patch("src.dashboard_service.main._send_subscription_notifications", new_callable=AsyncMock) as mock_notify:
        response = client.post("/subscriptions?subscriber_user_id=user1&channel_user_id=channel1")
        assert response.status_code == 200
        assert response.json()["subscribed"] is True
        mock_notify.assert_awaited_once_with("user1", "channel1")

    list_response = client.get("/subscriptions?user_id=user1")
    assert list_response.status_code == 200
    assert list_response.json()["channel_user_ids"] == ["channel1"]


def test_subscribe_is_idempotent(client):
    with patch("src.dashboard_service.main._send_subscription_notifications", new_callable=AsyncMock) as mock_notify:
        first = client.post("/subscriptions?subscriber_user_id=user1&channel_user_id=channel1")
        second = client.post("/subscriptions?subscriber_user_id=user1&channel_user_id=channel1")

        assert first.status_code == 200
        assert second.status_code == 200
        # Only first subscribe should emit notifications.
        mock_notify.assert_awaited_once_with("user1", "channel1")

    list_response = client.get("/subscriptions?user_id=user1")
    assert list_response.status_code == 200
    assert list_response.json()["channel_user_ids"] == ["channel1"]
    assert list_response.json()["count"] == 1


def test_subscribe_self_returns_400(client):
    response = client.post("/subscriptions?subscriber_user_id=user1&channel_user_id=user1")
    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot subscribe to yourself"


def test_unsubscribe_success(client, test_db):
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="channel1")

    response = client.delete("/subscriptions?subscriber_user_id=user1&channel_user_id=channel1")
    assert response.status_code == 200
    assert response.json()["subscribed"] is False

    list_response = client.get("/subscriptions?user_id=user1")
    assert list_response.status_code == 200
    assert list_response.json()["channel_user_ids"] == []


def test_unsubscribe_not_found(client):
    response = client.delete("/subscriptions?subscriber_user_id=user1&channel_user_id=channel1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Subscription not found"
