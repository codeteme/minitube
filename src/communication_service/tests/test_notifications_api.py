def test_create_and_list_notifications(client):
    payload = {
        "type": "subscription",
        "recipient_user_ids": ["user_a", "user_b"],
        "title": "Subscribed",
        "message": "A subscription happened.",
        "actor_user_id": "user_x",
        "channel_id": "channel_1",
        "video_id": None,
    }

    create_res = client.post("/comm/notifications", json=payload)
    assert create_res.status_code == 200
    create_data = create_res.json()
    assert create_data["status"] == "routed"
    assert create_data["routed_count"] == 2
    assert set(create_data["routed_to"]) == {"user_a", "user_b"}
    assert len(create_data["notification_ids"]) == 2

    list_a = client.get("/comm/notifications?user_id=user_a")
    assert list_a.status_code == 200
    list_a_data = list_a.json()
    assert list_a_data["count"] == 1
    assert list_a_data["notifications"][0]["type"] == "subscription"
    assert list_a_data["notifications"][0]["title"] == "Subscribed"
    assert list_a_data["notifications"][0]["is_read"] is False


def test_mark_notifications_read(client):
    create_res = client.post(
        "/comm/notifications",
        json={
            "type": "new_video",
            "recipient_user_ids": ["reader_1"],
            "title": "New video uploaded",
            "message": "Uploader 2 posted a new video.",
            "actor_user_id": "2",
            "channel_id": "2",
            "video_id": "v_1",
        },
    )
    notification_id = create_res.json()["notification_ids"][0]

    mark_res = client.patch(
        "/comm/notifications/read",
        json={
            "notification_ids": [notification_id],
            "recipient_user_id": "reader_1",
        },
    )
    assert mark_res.status_code == 200
    assert mark_res.json()["updated_count"] == 1

    unread = client.get("/comm/notifications?user_id=reader_1&unread_only=true")
    assert unread.status_code == 200
    assert unread.json()["count"] == 0

    all_items = client.get("/comm/notifications?user_id=reader_1")
    assert all_items.status_code == 200
    assert all_items.json()["notifications"][0]["is_read"] is True


def test_mark_notifications_read_not_found(client):
    response = client.patch(
        "/comm/notifications/read",
        json={
            "notification_ids": ["missing-id"],
            "recipient_user_id": "nobody",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"
