"""
Admin Panel Script - Run: python admin.py
"""

import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from models import User
import random
import qrcode
import os


class AdminPanel:
    def __init__(self, service_account_path='serviceAccountKey.json'):
        try:
            firebase_admin.get_app()
        except ValueError:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()

    def import_from_csv(self, csv_file_path):
        """Import participants from CSV"""
        print(f"\n📂 Reading CSV file: {csv_file_path}")

        try:
            df = pd.read_csv(csv_file_path)

            required_columns = ['full_name', 'email', 'linkedin_url', 'genre_color', 'convo_tip']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            df['email'] = df['email'].str.lower().str.strip()
            df['genre_color'] = df['genre_color'].str.lower().str.strip()

            print(f"✅ Found {len(df)} participants in CSV file")

            users = []
            for _, row in df.iterrows():
                user = User(
                    full_name=row['full_name'],
                    email=row['email'],
                    linkedin_url=row['linkedin_url'],
                    genre_color=row['genre_color'],
                    convo_tip=row['convo_tip']
                )

                errors = user.validate()
                if errors:
                    print(f"\n❌ Validation errors for {user.full_name}:")
                    for error in errors:
                        print(f"   - {error}")
                    return False

                users.append(user)

            print("\n🎯 Assigning random targets...")
            users_with_targets = self._assign_targets(users)

            print("\n☁️  Uploading to Firebase...")
            self._upload_users(users_with_targets)

            print(f"\n✅ Successfully imported {len(users_with_targets)} participants!")

            return True

        except Exception as e:
            print(f"\n❌ Import failed: {str(e)}")
            return False

    def _assign_targets(self, users):
        """Randomly assign each user a target"""
        targets = users.copy()
        random.shuffle(targets)

        for i, user in enumerate(users):
            target = targets[i]
            if target.email == user.email:
                if i < len(targets) - 1:
                    targets[i], targets[i + 1] = targets[i + 1], targets[i]
                else:
                    targets[i], targets[0] = targets[0], targets[i]
                target = targets[i]

            user.target_email = target.email

        return users

    def _upload_users(self, users):
        """Upload users to Firestore"""
        batch = self.db.batch()
        users_ref = self.db.collection('users')

        user_id_map = {}

        for user in users:
            doc_ref = users_ref.document()
            user_dict = user.to_dict()
            user_dict.pop('target_id', None)
            batch.set(doc_ref, user_dict)
            user_id_map[user.email] = doc_ref.id

        batch.commit()

        batch = self.db.batch()

        for user in users:
            user_id = user_id_map[user.email]
            target_id = user_id_map[user.target_email]

            doc_ref = users_ref.document(user_id)
            batch.update(doc_ref, {'target_id': target_id})

        batch.commit()

    def generate_qr_codes(self, output_folder='qr_codes'):
        """Generate QR codes for all users"""
        print("\n🔲 Generating QR codes...")
        os.makedirs(output_folder, exist_ok=True)

        users_ref = self.db.collection('users')
        count = 0

        for doc in users_ref.stream():
            user_data = doc.to_dict()
            user_id = doc.id

            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(user_id)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            filename = f"{user_data.get('full_name', 'Unknown').replace(' ', '_')}_{user_data.get('genre_color')}.png"
            filepath = os.path.join(output_folder, filename)
            img.save(filepath)

            count += 1

        print(f"✅ Generated {count} QR codes in '{output_folder}' folder")


def main():
    """CLI interface"""
    admin = AdminPanel()

    print("\n" + "=" * 60)
    print("  🎯 MYSTERY NETWORKING - ADMIN PANEL")
    print("=" * 60)

    while True:
        print("\n📋 Available Commands:")
        print("1. Import from CSV")
        print("2. Generate QR codes")
        print("3. Exit")

        choice = input("\nSelect option (1-3): ").strip()

        if choice == '1':
            file_path = input("Enter CSV file path: ").strip()
            admin.import_from_csv(file_path)

        elif choice == '2':
            output_folder = input("Enter output folder (default: qr_codes): ").strip()
            if not output_folder:
                output_folder = 'qr_codes'
            admin.generate_qr_codes(output_folder)

        elif choice == '3':
            print("\n👋 Goodbye!")
            break

        else:
            print("❌ Invalid option")


if __name__ == '__main__':
    main()
