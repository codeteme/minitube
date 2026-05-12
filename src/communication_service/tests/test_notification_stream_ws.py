def test_notification_stream_requires_user_id(client):
    with client.websocket_connect("/comm/notifications/stream") as ws:
        payload = ws.receive_json()
        assert payload["type"] == "error"
        assert "user_id is required" in payload["message"]


def test_notification_stream_receives_created_notifications(client):
    target_user = "stream_user_1"

    with client.websocket_connect(f"/comm/notifications/stream?user_id={target_user}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"
        assert connected["user_id"] == target_user

        response = client.post(
            "/comm/notifications",
            json={
                "type": "direct_message",
                "recipient_user_ids": [target_user],
                "title": "New message from Alex",
                "message": "Hey, are you free this afternoon?",
                "actor_user_id": "alex",
                "channel_id": None,
                "video_id": None,
            },
        )
        assert response.status_code == 200

        pushed = ws.receive_json()
        assert pushed["type"] == "notification_created"
        assert pushed["notification"]["recipient_user_id"] == target_user
        assert pushed["notification"]["type"] == "direct_message"
        assert pushed["notification"]["title"] == "New message from Alex"
