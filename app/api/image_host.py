"""
Instagram's Graph API needs a publicly reachable image URL — it will not
accept a local file. imgbb offers a free API key and is the simplest way to
get a public URL for a locally generated meme/image in a self-hosted
prototype. Swap this out for S3/Cloudinary/etc. later if you outgrow it.
"""
import base64
import os
import requests

IMGBB_ENDPOINT = "https://api.imgbb.com/1/upload"


class ImageHostError(RuntimeError):
    pass


def upload_image(image_path: str, api_key: str = None) -> str:
    api_key = api_key or os.getenv("IMGBB_API_KEY")
    if not api_key:
        raise ImageHostError(
            "IMGBB_API_KEY is not set. Get a free key at https://api.imgbb.com/ "
            "and add it to your .env file."
        )
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read())

    resp = requests.post(IMGBB_ENDPOINT, data={"key": api_key, "image": encoded})
    data = resp.json()
    if not data.get("success"):
        raise ImageHostError(f"imgbb upload failed: {data}")
    return data["data"]["url"]
