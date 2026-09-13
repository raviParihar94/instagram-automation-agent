import sys
import os
from datetime import datetime

# Allow `app.*` imports when Streamlit launches this file directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from app.config.settings import Settings
from app.core.agent import run_pipeline
from app.core import db
from app.api.instagram_client import InstagramClient

load_dotenv()

st.set_page_config(page_title="Instagram Automation Agent", page_icon="\U0001F4F8", layout="wide")

settings = Settings()
config = settings.load_config()

st.title("\U0001F4F8 Instagram Automation Agent")
st.caption("Configure your niche once, then let the agent research trends, generate content, and post — automatically.")

tab_config, tab_run, tab_history = st.tabs(["\u2699\ufe0f Configuration", "\u25B6\ufe0f Run", "\U0001F4CA Posting History"])

# ---------------------------------------------------------------------------
# Configuration tab
# ---------------------------------------------------------------------------
with tab_config:
    st.subheader("Instagram credentials")
    col1, col2 = st.columns(2)
    with col1:
        access_token = st.text_input("Access Token", value=config.access_token, type="password")
    with col2:
        ig_user_id = st.text_input("IG User ID", value=config.ig_user_id)

    st.subheader("Content configuration")
    niche = st.text_input("Niche / topic", value=config.niche)
    content_type = st.selectbox(
        "Content type",
        options=["meme", "health_tip", "news", "custom"],
        index=["meme", "health_tip", "news", "custom"].index(config.content_type)
        if config.content_type in ["meme", "health_tip", "news", "custom"] else 0,
    )
    system_prompt = st.text_area(
        "System prompt (this is what tells the LLM exactly how to write your posts)",
        value=config.system_prompt,
        height=140,
    )
    search_keywords = st.text_input(
        "Trend research keywords (used to search what's currently trending)",
        value=config.search_keywords,
    )
    hashtag_count = st.slider("Hashtags per post", 0, 30, value=config.hashtag_count)

    st.subheader("Posting schedule")
    posts_per_day = st.number_input("Posts per day", min_value=1, max_value=10, value=config.posts_per_day)
    post_times_str = st.text_input(
        "Post times (24h HH:MM, comma-separated)",
        value=", ".join(config.post_times),
        help="Example: 09:30, 15:00, 20:00",
    )
    auto_post = st.toggle(
        "Enable fully automatic posting (scheduler will publish live to Instagram)",
        value=config.auto_post,
    )

    if st.button("\U0001F4BE Save Configuration", type="primary"):
        new_config = config.model_validate(
            {
                "access_token": access_token,
                "ig_user_id": ig_user_id,
                "niche": niche,
                "content_type": content_type,
                "system_prompt": system_prompt,
                "search_keywords": search_keywords,
                "hashtag_count": hashtag_count,
                "posts_per_day": posts_per_day,
                "post_times": [t.strip() for t in post_times_str.split(",") if t.strip()],
                "auto_post": auto_post,
            }
        )
        settings.save_config(new_config)
        st.success("Configuration saved. The scheduler picks this up automatically on its next tick.")

# ---------------------------------------------------------------------------
# Run tab
# ---------------------------------------------------------------------------
with tab_run:
    st.subheader("Run the pipeline manually")
    st.write("Use this to preview what the agent would generate before turning on full automation.")

    dry_run = st.checkbox("Dry run (generate everything but don't actually post to Instagram)", value=True)

    if st.button("\u25B6\ufe0f Run pipeline now"):
        current_config = settings.load_config()
        with st.spinner("Researching trends, generating content, rendering image, posting..."):
            result = run_pipeline(current_config, dry_run=dry_run)

        if result.get("error"):
            st.error(f"Pipeline failed: {result['error']}")
        else:
            st.success("Pipeline finished!")
            colA, colB = st.columns([1, 2])
            with colA:
                if result.get("image_path") and os.path.exists(result["image_path"]):
                    st.image(result["image_path"], caption="Generated image")
            with colB:
                st.markdown(f"**Trends used:**\n\n" + "\n".join(f"- {t}" for t in result.get("trends", [])))
                st.markdown(f"**Caption:**\n\n{result.get('caption', '')}")
                if result.get("media_id"):
                    st.code(f"media_id: {result['media_id']}")

# ---------------------------------------------------------------------------
# Posting history / metrics tab
# ---------------------------------------------------------------------------
with tab_history:
    st.subheader("Posting history & engagement")

    if st.button("\U0001F504 Refresh metrics from Instagram"):
        current_config = settings.load_config()
        if not current_config.access_token or not current_config.ig_user_id:
            st.warning("Add your Instagram credentials in the Configuration tab first.")
        else:
            client = InstagramClient(current_config.access_token, current_config.ig_user_id)
            posts = db.fetch_all_posts()
            updated = 0
            for p in posts:
                if p["status"] == "posted" and p["media_id"]:
                    try:
                        metrics = client.get_media_insights(p["media_id"])
                        db.update_metrics(p["media_id"], metrics["likes"], metrics["comments"], metrics["reach"])
                        updated += 1
                    except Exception as e:
                        st.warning(f"Could not refresh {p['media_id']}: {e}")
            st.success(f"Refreshed metrics for {updated} post(s).")

    posts = db.fetch_all_posts()
    if not posts:
        st.info("No posts yet. Run the pipeline from the Run tab to create your first one.")
    else:
        df = pd.DataFrame(posts)
        df["created_at"] = df["created_at"].apply(lambda t: datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"))
        df = df[["created_at", "status", "caption", "likes", "comments", "reach", "media_id"]]
        st.dataframe(df, use_container_width=True, hide_index=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total posts", len(df))
        m2.metric("Total likes", int(df["likes"].sum()))
        m3.metric("Total reach", int(df["reach"].sum()))
