"""
Script to find and update the Busqueda.xlsx file to mark the campaign with ID 3398868
"""
import pandas as pd
from pathlib import Path

def find_and_mark_campaign():
    """Find the campaign with ID 3398868 and mark it for processing"""
    file_path = "/Users/andresgaibor/code/python/acumba-automation/data/Busqueda.xlsx"
    
    print(f"🔍 Finding and marking campaign ID 3398868 in {file_path}")
    print("=" * 60)
    
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        print(f"📊 Loaded file: {df.shape[0]} rows x {df.shape[1]} columns")
        
        # Find the row with campaign ID 3398868
        target_row_idx = df[df['ID Campaña'] == 3398868].index
        print(f"Target row indices: {target_row_idx.tolist()}")
        
        if len(target_row_idx) > 0:
            # Mark the campaign for processing by setting 'Buscar' to 'x'
            row_idx = target_row_idx[0]
            print(f"✅ Found campaign ID 3398868 at row {row_idx}")
            print(f"   Current 'Buscar' value: {df.loc[row_idx, 'Buscar']}")
            print(f"   Campaign name: {df.loc[row_idx, 'Nombre']}")
            
            # Update the 'Buscar' column to 'x' for this row
            df.loc[row_idx, 'Buscar'] = 'x'
            print(f"   Updated 'Buscar' value to: {df.loc[row_idx, 'Buscar']}")
            
            # Save the updated Excel file
            df.to_excel(file_path, index=False, engine="openpyxl")
            print(f"✅ Updated file saved successfully!")
            
        else:
            print(f"❌ Campaign ID 3398868 not found in the file")
            
            # Let's check if we can find any campaigns with "Puesta en Marcha" in the name
            matching_rows = df[df['Nombre'].str.contains("Puesta en Marcha", na=False)]
            print(f"\n🔍 Found {len(matching_rows)} campaigns with 'Puesta en Marcha' in the name:")
            for idx, row in matching_rows.iterrows():
                print(f"   Row {idx}: ID {row['ID Campaña']}, Nombre: {row['Nombre']}")
                
                # Mark the first matching campaign
                if pd.isna(df.loc[idx, 'Buscar']) or df.loc[idx, 'Buscar'] == '':
                    df.loc[idx, 'Buscar'] = 'x'
                    print(f"   ✅ Marked campaign {row['ID Campaña']} for processing")
            
            # Save the updated Excel file if we found and marked any campaigns
            if len(matching_rows) > 0:
                df.to_excel(file_path, index=False, engine="openpyxl")
                print(f"✅ Updated file saved with matching campaign marked!")
    
    except Exception as e:
        print(f"❌ Error updating file: {e}")
        import traceback
        traceback.print_exc()

def main():
    find_and_mark_campaign()

if __name__ == "__main__":
    main()