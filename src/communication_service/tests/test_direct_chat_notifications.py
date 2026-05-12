def test_direct_chat_offline_peer_creates_notification(client):
    user_a = "dm_sender_1"
    user_b = "dm_receiver_1"

    with client.websocket_connect(
        f"/comm/direct-chat?user_id={user_a}&username=Alice&peer_id={user_b}"
    ) as ws_a:
        history = ws_a.receive_json()
        assert history["type"] == "history"

        ws_a.send_json({"message": "hello while you are offline"})
        event = ws_a.receive_json()
        assert event["type"] == "direct_message"

    inbox = client.get(f"/comm/notifications?user_id={user_b}")
    assert inbox.status_code == 200
    inbox_data = inbox.json()
    assert inbox_data["count"] == 1
    item = inbox_data["notifications"][0]
    assert item["type"] == "direct_message"
    assert item["actor_user_id"] == user_a
    assert item["title"] == "New message from Alice"


def test_direct_chat_online_peer_does_not_create_notification(client):
    user_a = "dm_sender_2"
    user_b = "dm_receiver_2"

    with client.websocket_connect(
        f"/comm/direct-chat?user_id={user_a}&username=Alice&peer_id={user_b}"
    ) as ws_a, client.websocket_connect(
        f"/comm/direct-chat?user_id={user_b}&username=Bob&peer_id={user_a}"
    ) as ws_b:
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"message": "hello while you are online"})
        msg_a = ws_a.receive_json()
        msg_b = ws_b.receive_json()
        assert msg_a["type"] == "direct_message"
        assert msg_b["type"] == "direct_message"

    inbox = client.get(f"/comm/notifications?user_id={user_b}")
    assert inbox.status_code == 200
    assert inbox.json()["count"] == 0
