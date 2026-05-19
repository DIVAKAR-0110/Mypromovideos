"""
youtube_service.py — Fetches real YouTube channel & video data.
Uses YouTube Data API v3.
"""

import re
import math
import logging
from googleapiclient.discovery import build
from django.conf import settings

logger = logging.getLogger(__name__)


def _youtube_client():
    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is not set in environment variables.")
    return build("youtube", "v3", developerKey=api_key)


def search_channel(query: str) -> dict | None:
    try:
        yt = _youtube_client()
        search_resp = yt.search().list(
            q=query,
            type="channel",
            part="snippet",
            maxResults=3,
        ).execute()

        items = search_resp.get("items", [])
        if not items:
            return None

        channel_id = items[0]["snippet"]["channelId"]

        ch_resp = yt.channels().list(
            id=channel_id,
            part="snippet,statistics,contentDetails",
        ).execute()

        ch_items = ch_resp.get("items", [])
        if not ch_items:
            return None

        ch = ch_items[0]
        stats = ch.get("statistics", {})
        snippet = ch.get("snippet", {})

        return {
            "channel_id": channel_id,
            "channel_name": snippet.get("title", query),
            "description": snippet.get("description", "")[:300],
            "country": snippet.get("country", "N/A"),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_videos": int(stats.get("videoCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "playlist_id": ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "published_at": snippet.get("publishedAt", ""),
        }
    except Exception as e:
        logger.error(f"Error searching channel for '{query}': {e}")
        return None

def fetch_recent_videos(playlist_id: str, max_results: int = 30) -> list:
    """Fetch recent uploads from a channel's upload playlist."""
    if not playlist_id:
        return []
    try:
        yt = _youtube_client()
        videos = []
        next_page = None

        while len(videos) < max_results:
            resp = yt.playlistItems().list(
                playlistId=playlist_id,
                part="snippet,contentDetails",
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page,
            ).execute()

            video_ids = [
                item["contentDetails"]["videoId"]
                for item in resp.get("items", [])
                if item.get("contentDetails", {}).get("videoId")
            ]

            if not video_ids:
                break
            stats_resp = yt.videos().list(
                id=",".join(video_ids),
                part="snippet,statistics,contentDetails",
            ).execute()

            for v in stats_resp.get("items", []):
                s = v.get("statistics", {})
                sn = v.get("snippet", {})
                dur = _parse_duration(v.get("contentDetails", {}).get("duration", "PT0S"))
                videos.append({
                    "video_id": v["id"],
                    "title": sn.get("title", ""),
                    "description": sn.get("description", "")[:200],
                    "published_at": sn.get("publishedAt", ""),
                    "views": int(s.get("viewCount", 0)),
                    "likes": int(s.get("likeCount", 0)),
                    "comments": int(s.get("commentCount", 0)),
                    "duration_seconds": dur,
                    "tags": sn.get("tags", [])[:10],
                    "thumbnail": sn.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "url": f"https://youtube.com/watch?v={v['id']}",
                })

            next_page = resp.get("nextPageToken")
            if not next_page:
                break

        return videos
    except Exception as e:
        logger.error(f"Error fetching videos for playlist '{playlist_id}': {e}")
        return []


def _parse_duration(iso: str) -> int:
    """Convert ISO 8601 duration (e.g. PT4M13S) to total seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return h * 3600 + m * 60 + s


def compute_analytics(channel_info: dict, videos: list) -> dict:
    if not videos:
        return {
            "avg_views": 0,
            "avg_likes": 0,
            "avg_comments": 0,
            "avg_engagement_rate": 0,
            "top_videos": [],
            "posting_frequency_per_month": 0,
            "content_themes": [],
            "avg_duration_seconds": 0,
            "total_engagement": 0,
            "intelligence_score": 0,
        }

    n = len(videos)
    avg_views = sum(v["views"] for v in videos) / n
    avg_likes = sum(v["likes"] for v in videos) / n
    avg_comments = sum(v["comments"] for v in videos) / n
    avg_dur = sum(v["duration_seconds"] for v in videos) / n

    total_eng = []
    for v in videos:
        rate = ((v["likes"] + v["comments"]) / v["views"] * 100) if v["views"] > 0 else 0
        total_eng.append(rate)
    avg_eng = sum(total_eng) / n if total_eng else 0
    top = sorted(videos, key=lambda x: x["views"], reverse=True)[:5]
    from datetime import datetime, timezone
    dates = []
    for v in videos:
        try:
            dt = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
            dates.append(dt)
        except Exception:
            pass

    freq = 0
    if len(dates) >= 2:
        dates.sort()
        span_days = (dates[-1] - dates[0]).days or 1
        freq = round((len(dates) / span_days) * 30, 1)
    from collections import Counter
    tag_counter: Counter = Counter()
    for v in videos:
        for tag in v.get("tags", []):
            tag_counter[tag.lower()] += 1
        words = re.findall(r"\b[a-z]{4,}\b", v["title"].lower())
        for w in words:
            if w not in {"this", "that", "with", "from", "your", "their", "have", "will", "what", "when", "how", "about", "into"}:
                tag_counter[w] += 1

    themes = [t for t, _ in tag_counter.most_common(12)]
    base_score = (avg_eng * 5) + (min(freq, 30) * 1.5) + (math.log10(avg_views + 1) * 3)
    intelligence_score = round(min(max(base_score, 0), 100))

    return {
        "avg_views": round(avg_views),
        "avg_likes": round(avg_likes),
        "avg_comments": round(avg_comments),
        "avg_engagement_rate": round(avg_eng, 2),
        "top_videos": top,
        "posting_frequency_per_month": freq,
        "content_themes": themes,
        "avg_duration_seconds": round(avg_dur),
        "total_engagement": round(sum(v["likes"] + v["comments"] for v in videos)),
        "intelligence_score": intelligence_score,
    }
