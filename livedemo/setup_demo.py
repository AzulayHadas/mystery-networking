#!/usr/bin/env python3
"""
Live Demo Setup — generates demo data and starts the server.
Run: python setup_demo.py
"""
import pandas as pd
import os
import json
import random
import subprocess
import sys

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 6 demo participants across 3 teams ──────────────────────────
PARTICIPANTS = [
    {"full_name": "Alice Cohen",   "email": "alice@demo.com",  "linkedin_url": "https://linkedin.com/in/alicecohen",   "genre_color": "blue",  "convo_tip": "Ask about favorite tech stack",  "job_title": "Developer"},
    {"full_name": "Bob Levy",      "email": "bob@demo.com",    "linkedin_url": "https://linkedin.com/in/boblevy",      "genre_color": "blue",  "convo_tip": "Talk about side projects",       "job_title": "Backend Engineer"},
    {"full_name": "Carol Shapira", "email": "carol@demo.com",  "linkedin_url": "https://linkedin.com/in/carolshapira",  "genre_color": "red",   "convo_tip": "Discuss design trends",          "job_title": "UX Designer"},
    {"full_name": "Dan Mizrahi",   "email": "dan@demo.com",    "linkedin_url": "https://linkedin.com/in/danmizrahi",    "genre_color": "red",   "convo_tip": "Ask about career journey",       "job_title": "Product Manager"},
    {"full_name": "Eva Katz",      "email": "eva@demo.com",    "linkedin_url": "https://linkedin.com/in/evakatz",       "genre_color": "green", "convo_tip": "Talk about leadership style",    "job_title": "Team Lead"},
    {"full_name": "Frank Peretz",  "email": "frank@demo.com",  "linkedin_url": "https://linkedin.com/in/frankperetz",   "genre_color": "green", "convo_tip": "Discuss data insights",          "job_title": "Data Analyst"},
]

TEAMS = [
    {"color": "blue",  "name": "Tech Wizards",   "emoji": "\U0001f4bb", "description": "Tech Team"},
    {"color": "red",   "name": "Creative Minds",  "emoji": "\U0001f3a8", "description": "Design Team"},
    {"color": "green", "name": "Leaders",          "emoji": "\U0001f31f", "description": "PM Team"},
]

def generate_data():
    """Generate all CSV files needed for the demo."""
    random.seed(42)

    data_dir = os.path.join(DEMO_DIR, "data")
    qr_dir = os.path.join(DEMO_DIR, "qr_codes")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(qr_dir, exist_ok=True)

    # Stable user IDs (seeded so QR codes stay consistent)
    user_ids = ["a1b2c3d4", "e5f6a7b8", "c9d0e1f2", "a3b4c5d6", "e7f8a9b0", "c1d2e3f4"]
    for p, uid in zip(PARTICIPANTS, user_ids):
        p["user_id"] = uid

    # ── qr_mapping.csv  (what backend loads) ────────────────────
    qr_rows = []
    for p in PARTICIPANTS:
        qr_rows.append({
            "user_id":     p["user_id"],
            "full_name":   p["full_name"],
            "email":       p["email"],
            "job_title":   p["job_title"],
            "genre_color": p["genre_color"],
            "filename":    f"{p['full_name'].replace(' ', '_')}_{p['user_id']}.png",
            "filepath":    f"qr_codes/{p['full_name'].replace(' ', '_')}_{p['user_id']}.png",
        })
    pd.DataFrame(qr_rows).to_csv(os.path.join(qr_dir, "qr_mapping.csv"), index=False)

    # ── target_assignments.csv  (3 targets per person) ──────────
    assignments = []
    all_ids = [p["user_id"] for p in PARTICIPANTS]
    id_to_p = {p["user_id"]: p for p in PARTICIPANTS}

    for p in PARTICIPANTS:
        possible = [uid for uid in all_ids if uid != p["user_id"]]
        targets = random.sample(possible, 3)
        for tid in targets:
            t = id_to_p[tid]
            assignments.append({
                "scanner_id":       p["user_id"],
                "target_id":        tid,
                "target_name":      t["full_name"],
                "target_color":     t["genre_color"],
                "target_job_title": t["job_title"],
                "convo_tip":        t["convo_tip"],
            })
    pd.DataFrame(assignments).to_csv(os.path.join(qr_dir, "target_assignments.csv"), index=False)

    # ── participants.csv ────────────────────────────────────────
    pd.DataFrame([{
        "full_name":   p["full_name"],
        "email":       p["email"],
        "linkedin_url": p["linkedin_url"],
        "genre_color": p["genre_color"],
        "convo_tip":   p["convo_tip"],
    } for p in PARTICIPANTS]).to_csv(os.path.join(data_dir, "participants.csv"), index=False)

    # ── teams.csv ───────────────────────────────────────────────
    pd.DataFrame(TEAMS).to_csv(os.path.join(data_dir, "teams.csv"), index=False)

    # ── user_stats.json (empty) ─────────────────────────────────
    with open(os.path.join(data_dir, "user_stats.json"), "w") as f:
        json.dump({}, f)

    print("✅  Demo data generated")
    print(f"    {len(PARTICIPANTS)} participants  |  {len(assignments)} target assignments  |  {len(TEAMS)} teams")
    print()
    print("📧  Demo login emails:")
    for p in PARTICIPANTS:
        print(f"    {p['email']:20s}  ({p['full_name']}  —  {p['job_title']})")
    print()
    print("🔑  Demo QR user IDs (paste into scanner or scan QR):")
    for p in PARTICIPANTS:
        print(f"    {p['user_id']}  →  {p['full_name']}")


def start_server():
    """Start the Flask backend."""
    backend = os.path.join(DEMO_DIR, "backend", "app.py")
    print()
    print("=" * 55)
    print("  🚀  Starting Mystery Networking Live Demo")
    print("=" * 55)
    print()
    print("  Open in browser:")
    print("    🎯 Participant  →  http://localhost:5000/frontend/participant.html")
    print("    📊 Dashboard    →  http://localhost:5000/frontend/dashboard.html")
    print("    👥 Admin        →  http://localhost:5000/frontend/admin.html")
    print("    🏠 Home         →  http://localhost:5000")
    print()
    subprocess.run([sys.executable, backend], cwd=DEMO_DIR)


if __name__ == "__main__":
    generate_data()
    start_server()
