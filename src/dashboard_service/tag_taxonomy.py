"""Central canonical tag taxonomy for dashboard and upload validation."""

from __future__ import annotations

import re

TAG_TAXONOMY_SEED: dict[str, dict[str, object]] = {
    "general": {"display_name": "General", "category": "general", "aliases": ["misc", "other"]},
    "entertainment": {"display_name": "Entertainment", "category": "general", "aliases": ["fun", "funny"]},
    "vlog": {"display_name": "Vlog", "category": "lifestyle", "aliases": ["daily-vlog", "day-in-my-life"]},
    "music": {"display_name": "Music", "category": "arts", "aliases": ["song", "cover", "concert"]},
    "gaming": {"display_name": "Gaming", "category": "games", "aliases": ["gameplay", "esports", "streamer"]},
    "sports": {"display_name": "Sports", "category": "sports", "aliases": ["football", "basketball", "soccer"]},
    "news": {"display_name": "News", "category": "current-events", "aliases": ["headlines", "breaking-news"]},
    "politics": {"display_name": "Politics", "category": "current-events", "aliases": ["government", "election"]},
    "education": {"display_name": "Education", "category": "knowledge", "aliases": ["learning", "lesson"]},
    "how-to": {"display_name": "Tutorial", "category": "knowledge", "aliases": ["tutorial", "how-to", "guide"]},
    "science": {"display_name": "Science", "category": "knowledge", "aliases": ["research", "experiment"]},
    "history": {"display_name": "History", "category": "knowledge", "aliases": ["historical", "archive"]},
    "documentary": {"display_name": "Documentary", "category": "knowledge", "aliases": ["doc", "docu"]},
    "technology": {"display_name": "Technology", "category": "knowledge", "aliases": ["tech", "gadgets"]},
    "business": {"display_name": "Business", "category": "business", "aliases": ["startup", "entrepreneurship"]},
    "finance": {"display_name": "Finance", "category": "business", "aliases": ["investing", "stocks", "economy"]},
    "food": {"display_name": "Food", "category": "lifestyle", "aliases": ["cooking", "recipe"]},
    "travel": {"display_name": "Travel", "category": "lifestyle", "aliases": ["trip", "tourism"]},
    "health": {"display_name": "Health", "category": "lifestyle", "aliases": ["wellness", "medical"]},
    "fitness": {"display_name": "Fitness", "category": "lifestyle", "aliases": ["workout", "exercise"]},
    "fashion": {"display_name": "Fashion", "category": "lifestyle", "aliases": ["style", "outfit"]},
    "beauty": {"display_name": "Beauty", "category": "lifestyle", "aliases": ["makeup", "skincare"]},
    "home": {"display_name": "Home", "category": "lifestyle", "aliases": ["interior", "home-improvement"]},
    "diy": {"display_name": "DIY", "category": "hobby", "aliases": ["crafts", "maker"]},
    "automotive": {"display_name": "Automotive", "category": "hobby", "aliases": ["cars", "vehicles"]},
    "pets": {"display_name": "Pets", "category": "animals", "aliases": ["dog", "cat", "animal"]},
    "nature": {"display_name": "Nature", "category": "outdoor", "aliases": ["wildlife", "outdoors"]},
    "family": {"display_name": "Family", "category": "social", "aliases": ["parenting", "home-life"]},
    "kids": {"display_name": "Kids", "category": "social", "aliases": ["children", "family-friendly"]},
    "comedy": {"display_name": "Comedy", "category": "entertainment", "aliases": ["sketch", "standup"]},
    "movies-tv": {"display_name": "Movies & TV", "category": "entertainment", "aliases": ["film", "series"]},
    "anime": {"display_name": "Anime", "category": "entertainment", "aliases": ["animation", "manga"]},
    "art": {"display_name": "Art", "category": "arts", "aliases": ["drawing", "painting"]},
    "photography": {"display_name": "Photography", "category": "arts", "aliases": ["photo", "camera"]},
    "dance": {"display_name": "Dance", "category": "arts", "aliases": ["choreography", "dance-cover"]},
    "podcast": {"display_name": "Podcast", "category": "format", "aliases": ["talk-show", "interview"]},
    "live-stream": {"display_name": "Live Stream", "category": "format", "aliases": ["livestream", "live"]},
    "shorts": {"display_name": "Shorts", "category": "format", "aliases": ["short-form", "short-video"]},
}


def normalize_tag(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value[:32].strip("-")


def canonical_seed_tags() -> list[str]:
    return [normalize_tag(key) for key in TAG_TAXONOMY_SEED.keys() if normalize_tag(key)]
