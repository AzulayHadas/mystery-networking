"""
QR Code Generator for Mystery Networking
Generates QR codes from CSV/Excel file with participant data
"""

import pandas as pd
import qrcode
import os
from PIL import Image, ImageDraw, ImageFont
import uuid
import argparse

def generate_qr_codes_from_csv(input_file, output_dir='qr_codes'):
    """
    Generate QR codes from CSV/Excel file
    
    Expected CSV columns:
    - full_name: Participant's full name
    - email: Participant's email (will be used as unique ID)
    - linkedin_url: LinkedIn profile URL (optional)
    - genre_color: Color category (red, blue, green, yellow)
    - convo_tip: Conversation starter tip (optional)
    """
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created directory: {output_dir}")
    
    # Read the input file
    print(f"📂 Reading file: {input_file}")
    
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    else:  # Excel file
        df = pd.read_excel(input_file)
    
    print(f"✅ Found {len(df)} participants")
    
    # Validate required columns
    required_columns = ['full_name', 'email']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Clean email column
    df['email'] = df['email'].str.lower().str.strip()
    
    # Generate QR codes
    generated_codes = []
    
    for index, row in df.iterrows():
        # Generate unique user ID (you can use email or generate UUID)
        user_id = str(uuid.uuid4())[:8]  # Short UUID
        # Or use email as ID: user_id = row['email']
        
        full_name = row['full_name']
        email = row['email']
        
        # QR Code content - this is what gets scanned
        qr_content = user_id
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Create a larger image with name and details
        img_width = 400
        img_height = 500
        
        # Create white background
        final_img = Image.new('RGB', (img_width, img_height), 'white')
        
        # Paste QR code (resize to fit)
        qr_size = 250
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        x_offset = (img_width - qr_size) // 2
        y_offset = 50
        final_img.paste(qr_img, (x_offset, y_offset))
        
        # Add text information
        draw = ImageDraw.Draw(final_img)
        
        try:
            # Try to use a nice font
            font_large = ImageFont.truetype("arial.ttf", 24)
            font_small = ImageFont.truetype("arial.ttf", 16)
        except:
            # Fallback to default font
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Add participant name
        text_y = y_offset + qr_size + 20
        draw.text((img_width//2, text_y), full_name, fill="black", 
                 font=font_large, anchor="mm")
        
        # Add user ID
        text_y += 40
        draw.text((img_width//2, text_y), f"ID: {user_id}", fill="gray", 
                 font=font_small, anchor="mm")
        
        # Add color badge if available
        if 'genre_color' in df.columns and pd.notna(row['genre_color']):
            color = str(row['genre_color']).lower()
            text_y += 30
            draw.text((img_width//2, text_y), f"Color: {color}", fill="blue", 
                     font=font_small, anchor="mm")
        
        # Save the QR code
        safe_filename = "".join(c for c in full_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_filename = safe_filename.replace(' ', '_')
        filename = f"{safe_filename}_{user_id}.png"
        filepath = os.path.join(output_dir, filename)
        
        final_img.save(filepath)
        
        generated_codes.append({
            'user_id': user_id,
            'full_name': full_name,
            'email': email,
            'filename': filename,
            'filepath': filepath
        })
        
        print(f"✅ Generated QR for {full_name} -> {filename}")
    
    # Save mapping file
    mapping_df = pd.DataFrame(generated_codes)
    mapping_file = os.path.join(output_dir, 'qr_mapping.csv')
    mapping_df.to_csv(mapping_file, index=False)
    
    print(f"\n🎯 Generated {len(generated_codes)} QR codes in '{output_dir}'")
    print(f"📝 Mapping saved to: {mapping_file}")
    
    return generated_codes

def main():
    parser = argparse.ArgumentParser(description='Generate QR codes from CSV/Excel file')
    parser.add_argument('input_file', help='Path to CSV or Excel file with participant data')
    parser.add_argument('-o', '--output', default='qr_codes', help='Output directory for QR codes')
    
    args = parser.parse_args()
    
    try:
        generate_qr_codes_from_csv(args.input_file, args.output)
        print("\n🎉 QR code generation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Example usage if run directly
    import sys
    
    if len(sys.argv) == 1:
        # Demo mode - use the existing participants file
        demo_file = "data/participants.csv"
        if os.path.exists(demo_file):
            print("🔧 Demo mode - using data/participants.csv")
            generate_qr_codes_from_csv(demo_file)
        else:
            print("Usage: python qr_generator.py <input_file.csv> [-o output_directory]")
            print("\nExample:")
            print("  python qr_generator.py participants.csv")
            print("  python qr_generator.py data.xlsx -o my_qr_codes")
            print("\nRequired CSV columns:")
            print("  - full_name: Participant's name")
            print("  - email: Participant's email")
            print("  - genre_color: Color category (optional)")
            print("  - linkedin_url: LinkedIn URL (optional)")
            print("  - convo_tip: Conversation tip (optional)")
    else:
        main()