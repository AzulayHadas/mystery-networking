import pandas as pd

# Sample participant data
participants = [
    {
        'full_name': 'John Doe',
        'email': 'john.doe@email.com',
        'linkedin_url': 'https://linkedin.com/in/johndoe',
        'genre_color': 'blue',
        'convo_tip': 'Ask about their favorite travel destination'
    },
    {
        'full_name': 'Jane Smith', 
        'email': 'jane.smith@email.com',
        'linkedin_url': 'https://linkedin.com/in/janesmith',
        'genre_color': 'red',
        'convo_tip': 'Discuss favorite books or movies'
    },
    {
        'full_name': 'Mike Johnson',
        'email': 'mike.johnson@email.com', 
        'linkedin_url': 'https://linkedin.com/in/mikejohnson',
        'genre_color': 'green',
        'convo_tip': 'Talk about hobby projects or side interests'
    },
    {
        'full_name': 'Sarah Wilson',
        'email': 'sarah.wilson@email.com',
        'linkedin_url': 'https://linkedin.com/in/sarahwilson', 
        'genre_color': 'yellow',
        'convo_tip': 'Ask about their career journey'
    },
    {
        'full_name': 'David Chen',
        'email': 'david.chen@email.com',
        'linkedin_url': 'https://linkedin.com/in/davidchen',
        'genre_color': 'purple',
        'convo_tip': 'Discuss technology trends'
    }
]

# Create DataFrame and save as CSV
df = pd.DataFrame(participants)
df.to_csv('data/participants.csv', index=False)

print("✅ Created sample participants.csv file with 5 test participants")
print("Participants:")
for p in participants:
    print(f"  - {p['full_name']} ({p['genre_color']})")