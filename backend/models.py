"""
Data Models for Mystery Networking System
"""

from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime


@dataclass
class User:
    """User/Participant model"""
    full_name: str
    email: str
    linkedin_url: str
    genre_color: str  # red, blue, green, yellow
    target_id: str = None
    convo_tip: str = ""
    current_score: int = 0
    scanned_users: List[str] = field(default_factory=list)
    found_target: bool = False
    color_scanned: Dict[str, bool] = field(default_factory=lambda: {
        'red': False,
        'blue': False,
        'green': False,
        'yellow': False
    })
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        """Convert to dictionary for Firestore"""
        return {
            'full_name': self.full_name,
            'email': self.email.lower().strip(),
            'linkedin_url': self.linkedin_url,
            'genre_color': self.genre_color,
            'target_id': self.target_id,
            'convo_tip': self.convo_tip,
            'current_score': self.current_score,
            'scanned_users': self.scanned_users,
            'found_target': self.found_target,
            'color_scanned': self.color_scanned,
            'created_at': self.created_at
        }

    def validate(self):
        """Validate user data"""
        errors = []

        if not self.full_name or len(self.full_name) < 2:
            errors.append("Full name must be at least 2 characters")

        if not self.email or '@' not in self.email:
            errors.append("Valid email is required")

        if not self.linkedin_url or 'linkedin.com' not in self.linkedin_url:
            errors.append("Valid LinkedIn URL is required")

        if self.genre_color not in ['red', 'blue', 'green', 'yellow']:
            errors.append("Genre color must be red, blue, green, or yellow")

        return errors


@dataclass
class Scan:
    """QR Scan model"""
    scanner_id: str
    scanned_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    points_awarded: int = 0
    scan_type: str = "regular"  # "regular", "target", "color_bonus"

    def to_dict(self):
        """Convert to dictionary for Firestore"""
        return {
            'scanner_id': self.scanner_id,
            'scanned_id': self.scanned_id,
            'timestamp': self.timestamp,
            'points_awarded': self.points_awarded,
            'scan_type': self.scan_type
        }

    def validate(self):
        """Validate scan data"""
        errors = []

        if not self.scanner_id:
            errors.append("Scanner ID is required")

        if not self.scanned_id:
            errors.append("Scanned ID is required")

        if self.scanner_id == self.scanned_id:
            errors.append("Cannot scan yourself")

        if self.scan_type not in ['regular', 'target', 'color_bonus']:
            errors.append("Invalid scan type")

        return errors
