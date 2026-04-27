"""
Scoring Engine for Mystery Networking
Handles all point calculations and bonuses
"""

from datetime import datetime
from firebase_admin import firestore

class ScoringEngine:
    """
    Point System:
    - Regular scan: 10 points
    - Finding target: 100 points
    - Color series bonus: 50 points (scan one person of each color)
    - Conversation complete: 5 points
    """
    
    POINTS_REGULAR_SCAN = 10
    POINTS_TARGET_FOUND = 100
    POINTS_COLOR_SERIES = 50
    POINTS_CONVERSATION = 5
    
    def __init__(self, db):
        self.db = db
    
    def process_scan(self, scanner_id, scanned_id, scanner_data, scanned_data):
        """
        Process a scan and calculate points
        """
        try:
            points_earned = 0
            is_target = False
            bonuses = []
            
            # Check if scanned user is the target
            target_id = scanner_data.get('target_id')
            if target_id == scanned_id:
                is_target = True
                points_earned += self.POINTS_TARGET_FOUND
                bonuses.append(f"🎯 Target Found: +{self.POINTS_TARGET_FOUND} points")
            else:
                points_earned += self.POINTS_REGULAR_SCAN
                bonuses.append(f"👋 New Connection: +{self.POINTS_REGULAR_SCAN} points")
            
            # Check for color series bonus
            color_bonus = self._check_color_series_bonus(
                scanner_data, 
                scanned_data.get('genre_color')
            )
            
            if color_bonus > 0:
                points_earned += color_bonus
                bonuses.append(f"🌈 Color Series Complete: +{color_bonus} points")
            
            # Update scanner's data
            self._update_scanner(
                scanner_id, 
                scanned_id, 
                points_earned, 
                is_target,
                scanned_data.get('genre_color'),
                scanner_data
            )
            
            # Record the scan
            self._record_scan(
                scanner_id, 
                scanned_id, 
                is_target, 
                points_earned
            )
            
            # Get conversation tip if target found
            convo_tip = None
            if is_target:
                convo_tip = scanner_data.get('convo_tip', 'Ask about their interests!')
            
            return {
                "success": True,
                "is_target": is_target,
                "points_earned": points_earned,
                "total_score": scanner_data.get('current_score', 0) + points_earned,
                "bonuses": bonuses,
                "scanned_user": {
                    "name": scanned_data.get('full_name'),
                    "color": scanned_data.get('genre_color'),
                    "linkedin": scanned_data.get('linkedin_url')
                },
                "conversation_tip": convo_tip
            }
            
        except Exception as e:
            print(f"Scoring error: {str(e)}")
            raise
    
    def _check_color_series_bonus(self, scanner_data, scanned_color):
        """Check if scanning this color completes the color series"""
        color_scanned = scanner_data.get('color_scanned', {
            'red': False,
            'blue': False,
            'green': False,
            'yellow': False
        })
        
        if color_scanned.get(scanned_color, False):
            return 0
        
        color_scanned[scanned_color] = True
        all_scanned = all(color_scanned.values())
        
        if all_scanned:
            return self.POINTS_COLOR_SERIES
        
        return 0
    
    def _update_scanner(self, scanner_id, scanned_id, points, is_target, scanned_color, scanner_data):
        """Update scanner's document with new data"""
        scanner_ref = self.db.collection('users').document(scanner_id)
        
        scanned_users = scanner_data.get('scanned_users', [])
        scanned_users.append(scanned_id)
        
        color_scanned = scanner_data.get('color_scanned', {
            'red': False,
            'blue': False,
            'green': False,
            'yellow': False
        })
        color_scanned[scanned_color] = True
        
        current_score = scanner_data.get('current_score', 0)
        new_score = current_score + points
        
        update_data = {
            'scanned_users': scanned_users,
            'current_score': new_score,
            'color_scanned': color_scanned,
            'last_scan': datetime.now()
        }
        
        if is_target:
            update_data['found_target'] = True
            update_data['target_found_at'] = datetime.now()
        
        scanner_ref.update(update_data)
    
    def _record_scan(self, scanner_id, scanned_id, is_target, points):
        """Record scan in scans collection for analytics"""
        scan_ref = self.db.collection('scans')
        
        scan_ref.add({
            'scanner_id': scanner_id,
            'scanned_id': scanned_id,
            'was_target': is_target,
            'points_earned': points,
            'timestamp': datetime.now()
        })
