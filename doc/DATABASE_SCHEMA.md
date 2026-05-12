# Database Schema (Media Server)

## Key Design Decisions

- Use **single Postgres instance** with multiple tables (not multiple DBs).
- Store avatar as **URL/path metadata** in DB, not raw image bytes.
- Use **normalized tables** for subscriptions and notifications.
- Keep API responses non-null where possible:
  - `bio: ""`
  - `avatar: "<default_url>"`
  - `subscribedTo: []`
  - `notifications: []`
- Standardize user IDs across all services (`BIGINT` or `UUID`, one choice only).

---

## Tentative Tables

## Identity & Profile

### `users`
- `id` (PK)
- `email` (unique, indexed, not null)
- `name` (not null)
- `role` (not null)
- `hashed_password` (not null)
- `is_active` (bool, default true)
- `created_at`
- `updated_at`

### `user_profiles`
- `user_id` (PK, FK -> users.id)
- `bio` (text, not null, default `''`)
- `avatar_url` (text, not null, default placeholder URL)
- optional: `avatar_storage_key`, `avatar_mime_type`
- `updated_at`

---

## Subscriptions & Preferences

### `subscriptions`
- `subscriber_user_id` (PK, FK -> users.id, indexed)
- `channel_user_id` (PK, FK -> users.id)
- `created_at`
- primary key: (`subscriber_user_id`, `channel_user_id`)

### `user_settings`
- `user_id` (PK, FK -> users.id)
- `preferences_json` (JSONB, not null, default `{}`)
- `updated_at`

---

## Video Domain

### `videos`
- `id` (PK)
- `uploader_user_id` (FK -> users.id)
- `title` (not null)
- `description` (text, default `''`)
- `category` (default `'Education'`)
- `visibility` (e.g., `public/private/unlisted`)
- `status` (e.g., `active/deleted`)
- `created_at`
- `updated_at`

### `video_assets`
- `id` (PK)
- `video_id` (FK -> videos.id)
- `kind` (`source`, `thumbnail`)
- `storage_path` (or `storage_url`)
- `original_filename`
- `content_type`
- `size_bytes`
- `created_at`

### `video_tags`
- `video_id` (FK -> videos.id)
- `tag` (text)
- unique constraint: (`video_id`, `tag`)

---

## Engagement & History

### `video_views`
- `id` (PK)
- `video_id` (FK -> videos.id)
- `user_id` (nullable FK -> users.id for anonymous views)
- `viewed_at`
- `watch_seconds`

### `video_likes`
- `user_id` (FK -> users.id)
- `video_id` (FK -> videos.id)
- `created_at`
- unique constraint: (`user_id`, `video_id`)

### `watch_history`
- `id` (PK, auto-increment)
- `user_id` (FK -> users.id, indexed)
- `video_id` (FK -> videos.id)
- `last_position_seconds` (default 0)
- `last_watched_at`
- unique constraint: (`user_id`, `video_id`)

### `search_history`
- `id` (PK, auto-increment)
- `user_id` (FK -> users.id, indexed)
- `query` (text, not null)
- `searched_at`

### `video_engagement_daily` (optional analytics table)
- `video_id`
- `date`
- `views_count`
- `likes_count`
- unique constraint: (`video_id`, `date`)

---

## Communication

### `notifications`
- `id` (PK)
- `type` (`new_video`, `subscription`, etc.)
- `recipient_user_id` (FK -> users.id, indexed)
- `actor_user_id` (nullable FK -> users.id)
- `video_id` (nullable FK -> videos.id)
- `title`
- `message`
- `is_read` (default false)
- `read_at` (nullable)
- `created_at`

### `chat_rooms`
- `id` (PK)
- `type` (`video_room`, `direct_room`)
- `video_id` (nullable FK -> videos.id)
- `created_at`

### `chat_room_members`
- `room_id` (FK -> chat_rooms.id)
- `user_id` (FK -> users.id)
- unique constraint: (`room_id`, `user_id`)

### `chat_messages`
- `id` (PK)
- `room_id` (FK -> chat_rooms.id)
- `sender_user_id` (FK -> users.id)
- `message`
- `created_at`