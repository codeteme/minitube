def test_realtime_chat_requires_all_query_params(client):
    with client.websocket_connect("/comm/real-time-chat?video_id=v1&user_id=u1") as ws:
        payload = ws.receive_json()
        assert payload["type"] == "error"
        assert "video_id, user_id and username are required" in payload["message"]


def test_realtime_chat_history_and_broadcast(client):
    video_id = "video_abc"

    with client.websocket_connect(
        f"/comm/real-time-chat?video_id={video_id}&user_id=u1&username=Alice"
    ) as ws_a, client.websocket_connect(
        f"/comm/real-time-chat?video_id={video_id}&user_id=u2&username=Bob"
    ) as ws_b:
        history_a = ws_a.receive_json()
        history_b = ws_b.receive_json()
        assert history_a["type"] == "history"
        assert history_b["type"] == "history"

        # Join system messages are broadcast to room participants.
        join_events = [
            ws_a.receive_json(),
            ws_a.receive_json(),
            ws_b.receive_json(),
        ]
        assert any(event["type"] == "system" and "joined the chat" in event["message"] for event in join_events)

        ws_a.send_json({"message": "hello room"})
        msg_a = ws_a.receive_json()
        msg_b = ws_b.receive_json()
        assert msg_a["type"] == "chat_message"
        assert msg_b["type"] == "chat_message"
        assert msg_a["message"] == "hello room"
        assert msg_b["message"] == "hello room"
