#!/usr/bin/env python3
"""
Generate small trial CSV files for upload testing.
Creates qr_mapping.csv, target_assignments.csv, participants.csv, and teams.csv
with a small number of participants.
"""

import pandas as pd
import uuid
import random
import os

# 6 trial participants across 3 teams
PARTICIPANTS = [
    {"full_name": "Alice Cohen", "email": "alice@trial.com", "linkedin_url": "https://linkedin.com/in/alicecohen", "genre_color": "blue", "convo_tip": "Ask about favorite tech stack", "job_title": "Developer"},
    {"full_name": "Bob Levy", "email": "bob@trial.com", "linkedin_url": "https://linkedin.com/in/boblevy", "genre_color": "blue", "convo_tip": "Talk about side projects", "job_title": "Backend Engineer"},
    {"full_name": "Carol Shapira", "email": "carol@trial.com", "linkedin_url": "https://linkedin.com/in/carolshapira", "genre_color": "red", "convo_tip": "Discuss design trends", "job_title": "UX Designer"},
    {"full_name": "Dan Mizrahi", "email": "dan@trial.com", "linkedin_url": "https://linkedin.com/in/danmizrahi", "genre_color": "red", "convo_tip": "Ask about career journey", "job_title": "Product Manager"},
    {"full_name": "Eva Katz", "email": "eva@trial.com", "linkedin_url": "https://linkedin.com/in/evakatz", "genre_color": "green", "convo_tip": "Talk about leadership style", "job_title": "Team Lead"},
    {"full_name": "Frank Peretz", "email": "frank@trial.com", "linkedin_url": "https://linkedin.com/in/frankperetz", "genre_color": "green", "convo_tip": "Discuss data insights", "job_title": "Data Analyst"},
]

TEAMS = [
    {"color": "blue", "name": "Tech Wizards", "emoji": "💻", "description": "Tech Team"},
    {"color": "red", "name": "Creative Minds", "emoji": "🎨", "description": "Design Team"},
    {"color": "green", "name": "Leaders", "emoji": "🌟", "description": "PM Team"},
]

COLORS = ["red", "blue", "green"]

OUTPUT_DIR = "qr_codes_trial"


def main():
    random.seed(42)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Generate user IDs
    for p in PARTICIPANTS:
        p["user_id"] = str(uuid.uuid4())[:8]

    # --- qr_mapping.csv ---
    qr_rows = []
    for p in PARTICIPANTS:
        filename = f"{p['full_name'].replace(' ', '_')}_{p['user_id']}.png"
        qr_rows.append({
            "user_id": p["user_id"],
            "full_name": p["full_name"],
            "email": p["email"],
            "filename": filename,
            "filepath": f"{OUTPUT_DIR}\\{filename}",
        })
    qr_df = pd.DataFrame(qr_rows)
    qr_path = os.path.join(OUTPUT_DIR, "qr_mapping.csv")
    qr_df.to_csv(qr_path, index=False)
    print(f"✅ {qr_path}  ({len(qr_rows)} participants)")

    # --- target_assignments.csv ---
    # Each participant gets 3 targets (everyone except themselves, pick 3)
    assignments = []
    all_ids = [p["user_id"] for p in PARTICIPANTS]
    id_to_p = {p["user_id"]: p for p in PARTICIPANTS}

    for p in PARTICIPANTS:
        possible = [uid for uid in all_ids if uid != p["user_id"]]
        targets = random.sample(possible, min(3, len(possible)))
        for i, tid in enumerate(targets):
            t = id_to_p[tid]
            assignments.append({
                "scanner_id": p["user_id"],
                "scanner_name": p["full_name"],
                "target_id": tid,
                "target_name": t["full_name"],
                "target_color": COLORS[i % len(COLORS)],
                "target_job_title": t["job_title"],
                "convo_tip": t["convo_tip"],
            })
    assign_df = pd.DataFrame(assignments)
    assign_path = os.path.join(OUTPUT_DIR, "target_assignments.csv")
    assign_df.to_csv(assign_path, index=False)
    print(f"✅ {assign_path}  ({len(assignments)} assignments)")

    # --- participants.csv ---
    parts_df = pd.DataFrame([{
        "full_name": p["full_name"],
        "email": p["email"],
        "linkedin_url": p["linkedin_url"],
        "genre_color": p["genre_color"],
        "convo_tip": p["convo_tip"],
    } for p in PARTICIPANTS])
    parts_path = os.path.join("data", "participants_trial.csv")
    parts_df.to_csv(parts_path, index=False)
    print(f"✅ {parts_path}  ({len(PARTICIPANTS)} participants)")

    # --- teams.csv ---
    teams_df = pd.DataFrame(TEAMS)
    teams_path = os.path.join("data", "teams_trial.csv")
    teams_df.to_csv(teams_path, index=False)
    print(f"✅ {teams_path}  ({len(TEAMS)} teams)")

    # Summary
    print(f"\n📋 Trial data summary:")
    print(f"   Participants: {len(PARTICIPANTS)}")
    print(f"   Teams: {len(TEAMS)}")
    print(f"   Target assignments: {len(assignments)} (3 per person)")
    print()
    print("To use for the backend, copy trial files into qr_codes/:")
    print(f"   copy {OUTPUT_DIR}\\qr_mapping.csv qr_codes\\qr_mapping.csv")
    print(f"   copy {OUTPUT_DIR}\\target_assignments.csv qr_codes\\target_assignments.csv")
    print(f"   copy data\\participants_trial.csv data\\participants.csv")
    print(f"   copy data\\teams_trial.csv data\\teams.csv")


if __name__ == "__main__":
    main()
