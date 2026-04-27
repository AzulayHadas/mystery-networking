#!/usr/bin/env python3
"""
Generate Multiple Target Assignments
Creates a CSV file where each participant has 3 different targets to find.
"""

import pandas as pd
import random
import os

def generate_multiple_target_assignments():
    """Generate target assignments where each user has 3 targets"""
    
    # Read existing QR mapping to get all participants
    qr_mapping_file = 'qr_codes/qr_mapping.csv'
    if not os.path.exists(qr_mapping_file):
        print(f"❌ Error: {qr_mapping_file} not found")
        return
    
    qr_df = pd.read_csv(qr_mapping_file)
    
    # Read participant data to get names and jobs
    participants_file = 'data/participants.csv'
    if not os.path.exists(participants_file):
        print(f"❌ Error: {participants_file} not found")
        return
    
    participants_df = pd.read_csv(participants_file)
    
    # Create mapping of email to participant info
    # Since there's no job_title in Excel, we'll assign default jobs
    default_jobs = ['Software Engineer', 'Marketing Manager', 'Product Designer', 'Data Scientist', 'Tech Lead']
    
    email_to_info = {}
    for i, row in participants_df.iterrows():
        email_to_info[row['email']] = {
            'name': row['full_name'], 
            'job': default_jobs[i % len(default_jobs)],  # Cycle through job titles
            'convo_tip': row['convo_tip']
        }
    
    # Create mapping of user_id to email and info
    user_mapping = {}
    for _, row in qr_df.iterrows():
        user_id = row['user_id']
        email = row['email']
        if email in email_to_info:
            user_mapping[user_id] = {
                'email': email,
                'name': email_to_info[email]['name'],
                'job': email_to_info[email]['job'],
                'convo_tip': email_to_info[email]['convo_tip']
            }
    
    # Define colors for variety
    colors = ['red', 'blue', 'green', 'yellow', 'purple']
    
    # Generate assignments where each user gets 3 different targets
    assignments = []
    all_users = list(user_mapping.keys())
    
    for scanner_id in all_users:
        # Get all possible targets (everyone except themselves)
        possible_targets = [uid for uid in all_users if uid != scanner_id]
        
        # Randomly select 3 targets for this scanner
        if len(possible_targets) >= 3:
            selected_targets = random.sample(possible_targets, 3)
        else:
            # If we have fewer than 3 other users, select all available
            selected_targets = possible_targets
        
        # Create assignment entries
        for i, target_id in enumerate(selected_targets):
            assignments.append({
                'scanner_id': scanner_id,
                'scanner_name': user_mapping[scanner_id]['name'],
                'target_id': target_id,
                'target_name': user_mapping[target_id]['name'], 
                'target_color': colors[i % len(colors)],  # Cycle through colors
                'target_job_title': user_mapping[target_id]['job'],
                'convo_tip': user_mapping[target_id]['convo_tip']
            })
    
    # Create DataFrame and save to CSV
    assignments_df = pd.DataFrame(assignments)
    output_file = 'qr_codes/target_assignments.csv'
    assignments_df.to_csv(output_file, index=False)
    
    print(f"✅ Generated {len(assignments)} target assignments")
    print(f"📄 Saved to: {output_file}")
    
    # Show summary
    scanners = assignments_df['scanner_id'].nunique()
    targets_per_scanner = len(assignments) / scanners if scanners > 0 else 0
    print(f"👥 {scanners} participants, each with {targets_per_scanner:.1f} targets on average")
    
    # Show first few entries
    print("\n📋 Sample assignments:")
    print(assignments_df.head(10).to_string(index=False))

if __name__ == '__main__':
    random.seed(42)  # For consistent results
    generate_multiple_target_assignments()