#!/usr/bin/env python3
"""
Run 5 different game simulations with varied play patterns.
Detects and reports any issues found.
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from unittest.mock import patch
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))

def boot_app():
    """Fresh app instance for each game."""
    for mod in ['app', 'scoring']:
        if mod in sys.modules:
            del sys.modules[mod]
    with patch('firebase_admin.credentials.Certificate', side_effect=Exception("no creds")), \
         patch('firebase_admin.initialize_app'):
        import app as app_module

    qr_df = pd.read_csv(os.path.join(BASE, 'qr_codes_trial', 'qr_mapping.csv'))
    assign_df = pd.read_csv(os.path.join(BASE, 'qr_codes_trial', 'target_assignments.csv'))
    parts_df = pd.read_csv(os.path.join(BASE, 'data', 'participants_trial.csv'))

    app_module.db = None
    app_module.scorer = None
    app_module.qr_mapping = dict(zip(qr_df['user_id'], qr_df['email']))
    app_module.email_to_userid = dict(zip(qr_df['email'], qr_df['user_id']))
    app_module.target_assignments = dict(zip(assign_df['scanner_id'], assign_df['target_id']))
    app_module.target_assignments_df = assign_df

    participants = {}
    for _, row in parts_df.iterrows():
        email = row['email'].lower().strip()
        participants[email] = {
            'full_name': row['full_name'], 'email': email,
            'linkedin_url': row.get('linkedin_url', ''),
            'genre_color': row.get('genre_color', 'blue'),
            'convo_tip': row.get('convo_tip', ''),
        }
    app_module.participants_data = participants
    app_module.user_stats = {uid: {'total_score': 0, 'scanned_users': [], 'found_target': False}
                             for uid in app_module.qr_mapping}

    return app_module

# Player IDs
ALICE = '7963d4da'
BOB   = '647d03d2'
CAROL = 'a93eb187'
DAN   = '1c5e4799'
EVA   = '107914b0'
FRANK = '7b4d256b'
NAMES = {ALICE:'Alice', BOB:'Bob', CAROL:'Carol', DAN:'Dan', EVA:'Eva', FRANK:'Frank'}
ALL = [ALICE, BOB, CAROL, DAN, EVA, FRANK]

issues = []

def run_game(title, play_func):
    """Run one game simulation, catch and report issues."""
    print(f"\n{'='*60}")
    print(f"  🎮 {title}")
    print(f"{'='*60}")
    try:
        app = boot_app()
        c = app.app.test_client()
        errors = play_func(app, c)
        if errors:
            for e in errors:
                issues.append(f"[{title}] {e}")
                print(f"  ❌ {e}")
        else:
            print(f"  ✅ No issues found")
    except Exception as ex:
        msg = f"CRASH: {ex}"
        issues.append(f"[{title}] {msg}")
        print(f"  ❌ {msg}")
        traceback.print_exc()


# ═══════════════════════════════════════════
# GAME 1: Speed Run — Everyone finds all targets instantly
# ═══════════════════════════════════════════
def game1_speed_run(app, c):
    errors = []
    assign_df = app.target_assignments_df
    for uid in ALL:
        targets = assign_df[assign_df['scanner_id'] == uid]
        for _, t in targets.iterrows():
            r = c.post('/api/scan', json={'scanner_id': uid, 'scanned_id': t['target_id']})
            d = r.get_json()
            if r.status_code != 200:
                errors.append(f"{NAMES[uid]} scan {t['target_name']} failed: {d}")
            elif not d.get('is_target'):
                errors.append(f"{NAMES[uid]} → {t['target_name']} not recognized as target")
            elif d['points_earned'] != 100:
                errors.append(f"{NAMES[uid]} target scan gave {d['points_earned']} instead of 100")

    # Verify leaderboard
    lb = c.get('/api/leaderboard').get_json()
    for entry in lb:
        if entry['score'] != 300:
            errors.append(f"{entry['name']} has {entry['score']} pts, expected 300")
        if entry.get('scanned_count', 0) != 3:
            errors.append(f"{entry['name']} has {entry.get('scanned_count')} scans, expected 3")

    # Verify stats
    stats = c.get('/api/stats').get_json()
    if stats['total_scans'] != 18:
        errors.append(f"Expected 18 scans, got {stats['total_scans']}")
    if stats['completion_rate'] != 100.0:
        errors.append(f"Expected 100% completion, got {stats['completion_rate']}%")
    if stats['targets_found'] != 6:
        errors.append(f"Expected 6 targets found, got {stats['targets_found']}")

    print(f"  All 6 players found all 3 targets = 300 pts each")
    print(f"  18 total scans, 100% completion")
    return errors


# ═══════════════════════════════════════════
# GAME 2: Ghost Town — Nobody scans anyone
# ═══════════════════════════════════════════
def game2_ghost_town(app, c):
    errors = []

    # All login
    for uid in ALL:
        email = app.qr_mapping[uid]
        r = c.post('/api/auth/login', json={'email': email})
        d = r.get_json()
        if not d.get('success'):
            errors.append(f"Login failed for {NAMES[uid]}")
        if d['user'].get('current_score', 0) != 0:
            errors.append(f"{NAMES[uid]} has non-zero initial score")

    # Check targets available
    for uid in ALL:
        r = c.get(f'/api/user/{uid}/targets')
        d = r.get_json()
        if not isinstance(d.get('targets'), list):
            errors.append(f"Targets for {NAMES[uid]} not a list")
        elif len(d['targets']) != 3:
            errors.append(f"{NAMES[uid]} has {len(d['targets'])} targets, expected 3")

    # Stats should be all zeros
    stats = c.get('/api/stats').get_json()
    if stats['total_scans'] != 0:
        errors.append(f"Expected 0 scans, got {stats['total_scans']}")
    if stats['active_users'] != 0:
        errors.append(f"Expected 0 active, got {stats['active_users']}")

    # Leaderboard should have everyone at 0
    lb = c.get('/api/leaderboard').get_json()
    for entry in lb:
        if entry['score'] != 0:
            errors.append(f"{entry['name']} should have 0, has {entry['score']}")

    print(f"  Everyone logged in, nobody scanned. All zeros verified.")
    return errors


# ═══════════════════════════════════════════
# GAME 3: Chaos — Duplicate scans, self scans, invalid IDs
# ═══════════════════════════════════════════
def game3_chaos(app, c):
    errors = []

    # Self scan
    r = c.post('/api/scan', json={'scanner_id': ALICE, 'scanned_id': ALICE})
    if r.status_code != 400:
        errors.append(f"Self scan should be 400, got {r.status_code}")

    # Missing fields
    r = c.post('/api/scan', json={})
    if r.status_code != 400:
        errors.append(f"Empty scan should be 400, got {r.status_code}")

    r = c.post('/api/scan', json={'scanner_id': ALICE})
    if r.status_code != 400:
        errors.append(f"Missing scanned_id should be 400, got {r.status_code}")

    # Valid scan
    r = c.post('/api/scan', json={'scanner_id': ALICE, 'scanned_id': BOB})
    if r.status_code != 200:
        errors.append(f"Valid scan failed: {r.status_code}")

    # Duplicate
    r = c.post('/api/scan', json={'scanner_id': ALICE, 'scanned_id': BOB})
    if r.status_code != 400:
        errors.append(f"Duplicate scan should be 400, got {r.status_code}")

    # Unknown QR code
    r = c.post('/api/scan', json={'scanner_id': ALICE, 'scanned_id': 'totally_fake_id'})
    if r.status_code != 200:
        errors.append(f"Unknown QR should still return 200, got {r.status_code}")

    # Login with empty email
    r = c.post('/api/auth/login', json={'email': ''})
    if r.status_code != 400:
        errors.append(f"Empty email login should be 400, got {r.status_code}")

    # Login with unknown email (should fallback)
    r = c.post('/api/auth/login', json={'email': 'nobody@nowhere.com'})
    if r.status_code != 200:
        errors.append(f"Unknown email should get demo fallback 200, got {r.status_code}")

    # Score should only reflect the 1 valid + 1 unknown scan
    lb = c.get('/api/leaderboard').get_json()
    alice_entry = next((e for e in lb if e['id'] == ALICE), None)
    if alice_entry and alice_entry['score'] != 110:
        # 100 target + 10 unknown fallback
        errors.append(f"Alice score should be 110, got {alice_entry['score']}")

    print(f"  Self-scan blocked, duplicates blocked, missing fields blocked")
    print(f"  Unknown QR handled gracefully, empty/unknown email handled")
    return errors


# ═══════════════════════════════════════════
# GAME 4: Conversation Spam — Test convo point limits
# ═══════════════════════════════════════════
def game4_conversation_spam(app, c):
    errors = []

    # Bob completes 20 conversations without scanning anyone
    for i in range(20):
        r = c.post('/api/conversation/complete', json={'user_id': BOB})
        d = r.get_json()
        if not d.get('success'):
            errors.append(f"Conversation {i+1} failed")
        expected_score = (i + 1) * 5
        if d['new_score'] != expected_score:
            errors.append(f"After {i+1} convos, expected {expected_score}, got {d['new_score']}")

    # Leaderboard should show Bob at 100
    lb = c.get('/api/leaderboard').get_json()
    bob_entry = next((e for e in lb if e['id'] == BOB), None)
    if bob_entry and bob_entry['score'] != 100:
        errors.append(f"Bob should have 100 from 20 convos, got {bob_entry['score']}")

    # Now scan a target
    r = c.post('/api/scan', json={'scanner_id': BOB, 'scanned_id': DAN})
    d = r.get_json()
    if d.get('total_score') != 200:
        errors.append(f"Bob total after target scan should be 200, got {d.get('total_score')}")

    print(f"  20 conversations = 100 pts, then target scan = +100 = 200 total")
    return errors


# ═══════════════════════════════════════════
# GAME 5: Reset mid-game — Play, reset, play again
# ═══════════════════════════════════════════
def game5_reset_and_replay(app, c):
    errors = []

    # Phase 1: Some gameplay
    c.post('/api/scan', json={'scanner_id': ALICE, 'scanned_id': BOB})
    c.post('/api/scan', json={'scanner_id': BOB, 'scanned_id': CAROL})
    c.post('/api/scan', json={'scanner_id': CAROL, 'scanned_id': DAN})

    stats = c.get('/api/stats').get_json()
    if stats['total_scans'] != 3:
        errors.append(f"Pre-reset: expected 3 scans, got {stats['total_scans']}")

    # Reset
    r = c.post('/api/admin/reset-event')
    if r.status_code != 200:
        errors.append(f"Reset failed: {r.status_code}")

    # Verify clean slate
    stats = c.get('/api/stats').get_json()
    if stats['total_scans'] != 0:
        errors.append(f"Post-reset scans should be 0, got {stats['total_scans']}")
    if stats['active_users'] != 0:
        errors.append(f"Post-reset active should be 0, got {stats['active_users']}")

    # Phase 2: Play again — same scans should work (not duplicates)
    r = c.post('/api/scan', json={'scanner_id': ALICE, 'scanned_id': BOB})
    if r.status_code != 200:
        errors.append(f"Post-reset scan failed: {r.status_code} — {r.get_json()}")
    else:
        d = r.get_json()
        if not d.get('success'):
            errors.append(f"Post-reset scan not successful: {d}")

    r = c.post('/api/scan', json={'scanner_id': FRANK, 'scanned_id': EVA})
    if r.status_code != 200:
        errors.append(f"Frank post-reset scan failed: {r.status_code}")

    stats = c.get('/api/stats').get_json()
    if stats['total_scans'] != 2:
        errors.append(f"Post-reset round 2: expected 2 scans, got {stats['total_scans']}")

    print(f"  Game 1: 3 scans → reset → Game 2: 2 new scans OK")
    return errors


# ═══════════════════════════════════════════
# RUN ALL GAMES
# ═══════════════════════════════════════════
print("🎯 MYSTERY NETWORKING — MULTI-GAME STRESS TEST")
print("=" * 60)

run_game("GAME 1: Speed Run (all targets found)", game1_speed_run)
run_game("GAME 2: Ghost Town (no activity)", game2_ghost_town)
run_game("GAME 3: Chaos (invalid inputs)", game3_chaos)
run_game("GAME 4: Conversation Spam (20 convos)", game4_conversation_spam)
run_game("GAME 5: Reset & Replay", game5_reset_and_replay)

# ═══════════════════════════════════════════
# FINAL REPORT
# ═══════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  📋 FINAL REPORT")
print(f"{'='*60}")
if issues:
    print(f"\n  ❌ {len(issues)} ISSUES FOUND:")
    for i, issue in enumerate(issues, 1):
        print(f"    {i}. {issue}")
else:
    print(f"\n  ✅ ALL 5 GAMES PASSED — NO ISSUES FOUND")
print(f"\n{'='*60}")

sys.exit(1 if issues else 0)
