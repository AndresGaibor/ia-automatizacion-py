#!/usr/bin/env python3
"""
Test script to run the demo with additional debugging for URL scraping
"""
import sys
from pathlib import Path

# Add the project root directory to the path 
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.demo import generar_general
from src.utils import load_config, crear_contexto_navegador, configurar_navegador
from src.autentificacion import login
from playwright.sync_api import sync_playwright
from dataclasses import dataclass
from typing import List

# Mock data classes for testing
@dataclass
class MockCampaign:
    name: str
    date: str
    lists: List[int]
    id: int

@dataclass
class MockCampaignComplete:
    total_delivered: int
    opened: int = None

class MockList:
    def __init__(self, id, name):
        self.id = id
        self.name = name

def test_generar_general_with_browser():
    \"\"\"
    Test the generar_general function in a browser context to ensure it works properly
    \"\"\"
    print(\"🔍 Testing generar_general function with actual browser context\")
    print(\"=\" * 60)
    
    try:
        with sync_playwright() as p:
            config = load_config()
            extraccion_oculta = bool(config.get(\"headless\", False))
            
            print(f\"🌐 Launching browser (headless: {extraccion_oculta})...\")
            browser = configurar_navegador(p, extraccion_oculta)
            context = crear_contexto_navegador(browser, extraccion_oculta)
            page = context.new_page()
            
            print(\"🔐 Logging in to Acumbamail...\")
            login(page, context=context)
            
            # Create mock data to test the function - using actual campaign data
            # The campaign we know has URLs: 3398868
            test_campaign = MockCampaign(
                name=\"20250924_Com_Puesta en Marcha_EVID_CA 1_Madrid Capital\",
                date=\"2025-09-24\",
                lists=[1165864, 1163824, 1165705, 1170350],  # From the logs we saw earlier
                id=3398868  # The campaign with known URLs
            )
            
            test_campaign_complete = MockCampaignComplete(
                total_delivered=100,  # Placeholder value
                opened=50             # Placeholder value
            )
            
            test_lists = [
                MockList(1165864, \"YOLANDA CAMPILLO\"),
                MockList(1163824, \"Equipo_Minsait\"), 
                MockList(1165705, \"Equipo EVID\"),
                MockList(1170350, \"EVID CONTENCIOSO 1 GTA LAJ BG\")
            ]
            
            print(f\"🔗 Testing generar_general with campaign ID: {test_campaign.id}\")
            print(f\"   Campaign has 'id' attribute: {hasattr(test_campaign, 'id')}\")
            print(f\"   Campaign ID value: {getattr(test_campaign, 'id', 'NOT_FOUND')}\")
            
            # Call the function
            result = generar_general(test_campaign, test_campaign_complete, [], test_lists, page)
            
            print(f\"✅ generar_general returned: {result}\")
            print(f\"📊 Result length: {len(result)}\")
            
            if len(result) >= 8:
                url_value = result[7]  # The URL de Correo column
                print(f\"🔗 URL de Correo value: '{url_value}'\")
                
                if url_value and url_value.strip():
                    print(\"✅ SUCCESS: URLs were successfully extracted and included!\")
                    return True
                else:
                    print(\"❌ FAILURE: URL de Correo column is empty\")
                    return False
            else:
                print(f\"❌ FAILURE: Result doesn't have enough elements: {result}\")
                return False
            
            browser.close()
            print(\"✅ Browser closed\")
        
    except Exception as e:
        print(f\"❌ Error during testing: {e}\")
        import traceback
        traceback.print_exc()
        return False

def main():
    print(\"🚀 Testing URL Scraping Integration with generar_general Function\")
    print(\"=\" * 60)
    
    success = test_generar_general_with_browser()
    
    if success:
        print(\"\\n🎉 SUCCESS: Function integration is working properly!\")
    else:
        print(\"\\n❌ FAILURE: There's an issue with the function integration\")
    
    return success

if __name__ == \"__main__\":
    main()