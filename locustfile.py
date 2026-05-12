import os

import random

from locust import HttpUser, task, between

WAIT = between(0.5, 2.0)

AUTH_EMAIL = os.environ.get("LOCUST_AUTH_EMAIL", "loadtest@example.com")
AUTH_PASSWORD = os.environ.get("LOCUST_AUTH_PASSWORD", "Loadtest1")

USER_ID = os.environ.get("LOCUST_USER_ID", "1")

# Simulate users hitting the AuthService API
class AuthServiceUser(HttpUser):
    
    host = "http://localhost:8003"

    wait_time = WAIT

    def on_start(self):
        self.token = None
        with self.client.post(
            "/auth/login/",
            data={"username": AUTH_EMAIL, "password": AUTH_PASSWORD},
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                self.token = r.json().get("access_token")
            else:
                r.failure(f"login failed: {r.status_code}")

    def _headers(self):
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(4)
    def verify_token(self):
        self.client.get("/verify-token/", headers=self._headers())

    @task(3)
    def profile(self):
        self.client.get("/profile/", headers=self._headers())

    @task(1)
    def health(self):
        self.client.get("/health", name="Auth API /health")

class VideoServiceUser(HttpUser):
    host = "http://localhost:8000"
    wait_time = WAIT

    def on_start(self):
        self.video_id = None
        with self.client.get("/videos", catch_response=True) as r:
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    self.video_id = data[0].get("id") # Get the first video id

    @task(4)
    def list_videos(self):
        self.client.get("/videos")

    @task(2)
    def ping(self):
        self.client.get("/videos/ping")

    @task(2)
    def video_detail(self):
        if not self.video_id:
            return
        self.client.get(f"/videos/{self.video_id}")

    @task(1)
    def transcript(self):
        if not self.video_id:
            return
        self.client.get(f"/videos/{self.video_id}/transcript")

    @task(3)
    def play_video(self):
        if not self.video_id:
            return
        # Try partial content so load test doesn't always download entire file
        self.client.get(
            f"/videos/{self.video_id}/play",
            headers={"Range": "bytes=0-2047"},
            name="/videos/[id]/play",
        )

    @task(1)
    def thumbnail(self):
        if not self.video_id:
            return
        self.client.get(
            f"/videos/{self.video_id}/thumbnail",
            name="/videos/[id]/thumbnail",
        )

    @task(1)
    def record_view(self):
        if not self.video_id:
            return
        self.client.post(f"/videos/{self.video_id}/view")

class DashboardServiceUser(HttpUser):
    host = "http://localhost:8004"
    wait_time = between(1, 3)

    def on_start(self):
        self.user_ids = ["1", "2", "3"]
        self.search_terms = ["python", "ai", "tutorial"]

    @task(5)
    def health(self):
        self.client.get("/health", name="Dashboard API /health")

    @task(4)
    def search(self):
        # Omit user_id to avoid writing search history on every request
        self.client.get(
            "/search",
            params={"q": random.choice(self.search_terms)},
        )

    @task(3)
    def search_suggestions(self):
        self.client.get(
            "/search/suggestions",
            params={"q": random.choice(self.search_terms)},
        )

    @task(3)
    def recommend(self):
        self.client.get("/dashboard/recommend", params={"user_id": random.choice(self.user_ids)})

    @task(3)
    def subscriptions_feed(self):
        self.client.get("/subscriptions/feed", params={"user_id": random.choice(self.user_ids)})

    @task(2)
    def watched_history(self):
        self.client.get("/user/history/watched", params={"user_id": random.choice(self.user_ids)})


class CommunicationServiceUser(HttpUser):
    host = "http://localhost:8002"
    wait_time = between(1, 3)

    def on_start(self):
        self.user_ids = ["1", "2", "3"]

    @task(5)
    def health(self):
        self.client.get("/health", name="Communication API /health")

    @task(1)
    def create_notification(self):
        self.client.post(
            "/comm/notifications",
            json={
                "type": "new_video",
                "recipient_user_ids": [random.choice(self.user_ids)],
                "title": "Load test",
                "message": "New video notification",
                "actor_user_id": "10",
                "channel_id": "10",
                "video_id": "v-1",
            },
        )

    @task(4)
    def list_notifications(self):
        self.client.get("/comm/notifications", params={"user_id": random.choice(self.user_ids)})


class IntelligenceServiceUser(HttpUser):
    host = "http://localhost:8005"
    wait_time = between(1, 3)

    @task(5)
    def health(self):
        self.client.get("/health", name="Intelligence API /health")

    @task(4)
    def ai_health(self):
        self.client.get("/ai/health", name="Intelligence API /ai/health")

    @task(1)
    def summarize(self):
        self.client.post(
            "/ai/summarize",
            json={
                "video_id": "v-1",
                "source_text": "This video explains FastAPI basics and API testing.",
                "source_kind": "subtitle_text",
                "max_sentences": 3,
            },
        )


class AdminServiceUser(HttpUser):
    host = "http://localhost:8001"
    wait_time = between(1, 3)

    @task(4)
    def health(self):
        self.client.get("/health", name="Admin API /health")

    @task(3)
    def admin_health(self):
        self.client.get("/admin/health", name="Admin API /admin/health")

    @task(2)
    def users_count(self):
        self.client.get("/admin/users/count", name="Admin API /admin/users/count")