"""
Runs as its own long-lived process (its own Docker service) so posting keeps
happening even if you close the dashboard tab. Reads config.json fresh on
every tick, so changes you save in the dashboard take effect on the next run
without needing a restart.
"""
import time
import schedule
from dotenv import load_dotenv

from app.config.settings import Settings
from app.core.agent import run_pipeline

load_dotenv()

_scheduled_times = set()


def job():
    settings = Settings()
    config = settings.load_config()
    if not config.auto_post:
        print("[scheduler] auto_post is OFF — skipping this slot. Enable it in the dashboard.")
        return
    if not config.access_token or not config.ig_user_id:
        print("[scheduler] Missing Instagram credentials — skipping.")
        return

    print(f"[scheduler] Running content pipeline for niche: {config.niche}")
    result = run_pipeline(config)
    if result.get("error"):
        print(f"[scheduler] Pipeline failed: {result['error']}")
    else:
        print(f"[scheduler] Posted successfully. media_id={result.get('media_id')}")


def sync_schedule():
    """Re-reads post_times from config every loop so dashboard edits apply live."""
    settings = Settings()
    config = settings.load_config()
    desired = set(config.post_times)
    if desired != _scheduled_times:
        schedule.clear()
        for t in config.post_times:
            schedule.every().day.at(t).do(job)
        _scheduled_times.clear()
        _scheduled_times.update(desired)
        print(f"[scheduler] Schedule updated. Posting daily at: {sorted(desired)}")


if __name__ == "__main__":
    print("[scheduler] Instagram Automation Agent scheduler started.")
    while True:
        sync_schedule()
        schedule.run_pending()
        time.sleep(30)
