"""
Entry point. Launches the Streamlit dashboard.
(The scheduler is a separate process — see app/core/scheduler_runner.py —
so posting keeps running even when the dashboard isn't open.)
"""
import subprocess

if __name__ == "__main__":
    subprocess.run(
        ["streamlit", "run", "app/ui/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
    )
