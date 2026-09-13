"""
Thin wrapper around the Instagram Graph API (via a Facebook professional/
business account linked to Instagram). Requires:
  - a Facebook Page connected to an Instagram Business/Creator account
  - a long-lived Page Access Token with instagram_basic + instagram_content_publish
  - the numeric Instagram User ID (ig_user_id)

Docs: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
"""
import requests


class InstagramClient:
    def __init__(self, access_token: str, user_id: str, api_version: str = "v20.0"):
        self.access_token = access_token
        self.user_id = user_id
        self.base_url = f"https://graph.facebook.com/{api_version}"

    def _check(self, resp: requests.Response) -> dict:
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Instagram API error: {data['error']}")
        return data

    def publish_image_post(self, image_url: str, caption: str) -> dict:
        """Two-step publish: create a media container, then publish it."""
        container_resp = requests.post(
            f"{self.base_url}/{self.user_id}/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.access_token,
            },
        )
        container = self._check(container_resp)
        media_id = container.get("id")
        if not media_id:
            raise RuntimeError(f"Failed to create media container: {container}")

        publish_resp = requests.post(
            f"{self.base_url}/{self.user_id}/media_publish",
            params={"creation_id": media_id, "access_token": self.access_token},
        )
        return self._check(publish_resp)

    def get_media_insights(self, media_id: str) -> dict:
        """Fetch likes/comments/reach for a published media object."""
        resp = requests.get(
            f"{self.base_url}/{media_id}",
            params={
                "fields": "like_count,comments_count",
                "access_token": self.access_token,
            },
        )
        basic = self._check(resp)

        insights_resp = requests.get(
            f"{self.base_url}/{media_id}/insights",
            params={"metric": "reach,impressions", "access_token": self.access_token},
        )
        reach = 0
        try:
            insights = self._check(insights_resp)
            for item in insights.get("data", []):
                if item.get("name") == "reach":
                    reach = item["values"][0]["value"]
        except RuntimeError:
            pass  # insights can be unavailable for some account types

        return {
            "likes": basic.get("like_count", 0),
            "comments": basic.get("comments_count", 0),
            "reach": reach,
        }
