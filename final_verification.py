"""
Final verification script to check if the newly generated Excel file contains URLs
"""
import pandas as pd
from pathlib import Path

def verify_new_excel_has_urls():
    \"\"\"
    Find the most recently created Excel file and verify it contains URLs
    \"\"\"
    suscriptores_dir = Path(\"/Users/andresgaibor/code/python/acumba-automation/data/suscriptores\")
    
    # Find the most recent Excel file with \"Puesta en Marcha\" in the name
    files = list(suscriptores_dir.glob(\"*Puesta en Marcha*\"))
    if not files:
        print(\"❌ No files found with 'Puesta en Marcha' in the name\")
        return False
    
    # Get the most recently modified file
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    print(f\"🔍 Checking most recent file: {latest_file.name}\")
    
    try:
        # Read the 'General' sheet
        df = pd.read_excel(latest_file, sheet_name='General', engine='openpyxl')
        print(f\"📊 Shape: {df.shape[0]} rows x {df.shape[1]} columns\")
        print(f\"📋 Columns: {list(df.columns)}\")
        
        # Check if 'URL de Correo' column exists and has data
        if 'URL de Correo' in df.columns:
            url_data = df['URL de Correo'].dropna()  # Remove NaN values
            if len(url_data) > 0 and any(pd.notna(url) and url.strip() for url in url_data):
                print(f\"\\n🔗 Found {len(url_data)} non-empty URL entries:\")
                for i, url in enumerate(url_data):
                    if pd.notna(url) and url.strip():  # Check if not NaN and not just whitespace
                        print(f\"   {i+1}. {url}\")
                
                # Check if URLs contain expected patterns
                valid_urls = [url for url in url_data if pd.notna(url) and str(url).startswith(('http://', 'https://'))]
                if valid_urls:
                    print(f\"\\n🎉 SUCCESS: Found {len(valid_urls)} valid URLs in 'URL de Correo' column\")
                    print(\"✅ The URL scraping functionality is now working correctly!\")
                    return True
                else:
                    print(f\"\\n❌ FAILURE: Entries found but they don't look like valid URLs\")
                    return False
            else:
                print(f\"\\n❌ FAILURE: No URLs found in 'URL de Correo' column\")
                return False
        else:
            print(f\"\\n❌ FAILURE: Column 'URL de Correo' not found in the sheet\")
            return False
    except Exception as e:
        print(f\"❌ Error reading Excel file: {e}\")
        import traceback
        traceback.print_exc()
        return False

def main():
    print(\"🚀 Final Verification: Checking if new Excel file contains URLs\")
    print(\"=\" * 80)
    
    success = verify_new_excel_has_urls()
    
    if success:
        print(\"\\n\" + \"=\" * 80)
        print(\"🎉 IMPLEMENTATION SUCCESSFUL!\")
        print(\"✅ URLs have been successfully scraped and included in the Excel report\")
        print(\"✅ The demo.py script is working correctly with the new functionality\")
    else:
        print(\"\\n\" + \"=\" * 80)
        print(\"❌ IMPLEMENTATION FAILED\")
        print(\"❌ The URL scraping functionality is not working as expected\")
    
    return success

if __name__ == \"__main__\":
    main()