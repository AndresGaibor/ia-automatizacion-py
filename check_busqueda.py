"""
Script to check the Busqueda.xlsx file and see if campaigns are marked for processing
"""
import pandas as pd
from pathlib import Path

def check_busqueda_file():
    """Check the Busqueda.xlsx file"""
    file_path = "/Users/andresgaibor/code/python/acumba-automation/data/Busqueda.xlsx"
    
    print(f"🔍 Checking Busqueda.xlsx file: {file_path}")
    print("=" * 60)
    
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        print(f"📊 Shape: {df.shape[0]} rows x {df.shape[1]} columns")
        print(f"📋 Columns: {list(df.columns)}")
        
        # Show first few rows to see the structure
        print(f"\n📄 First 5 rows:")
        print(df.head())
        
        # Check for campaigns marked for processing ('x' or 'X' in 'Buscar' column)
        if 'Buscar' in df.columns:
            marked_campaigns = df[df['Buscar'].isin(['x', 'X', '1'])]
            print(f"\n✅ Campaigns marked for processing: {len(marked_campaigns)}")
            
            if len(marked_campaigns) > 0:
                print("\n📋 Marked campaigns:")
                for idx, row in marked_campaigns.iterrows():
                    id_val = row.get('ID Campaña', 'N/A')
                    name_val = row.get('Nombre', 'N/A')
                    print(f"   - ID: {id_val}, Nombre: {name_val}")
            else:
                print("\n❌ No campaigns are marked for processing (Buscar column doesn't have 'x' or 'X')")
        else:
            print(f"\n❌ 'Buscar' column not found in the file")
    
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        import traceback
        traceback.print_exc()

def main():
    check_busqueda_file()

if __name__ == "__main__":
    main()