#!/usr/bin/env python3
"""
Test script for segment processing - comprehensive error case analysis
"""
import sys
import os
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

try:
    from src.descargar_suscriptores import extraer_suscriptores_tabla_lista
    from src.utils import crear_contexto_navegador, configurar_navegador, load_config
    from src.autentificacion import login
    from playwright.sync_api import sync_playwright, TimeoutError
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_segment_processing_comprehensive():
    """Test segment processing with comprehensive error analysis"""
    print("🧪 COMPREHENSIVE SEGMENT PROCESSING TEST")
    print("=" * 60)

    # Test cases with different segment lists
    test_cases = [
        {
            "name": "Prueba_SEGMENTOS",
            "url": "https://acumbamail.com/app/list/1169225/subscriber/list/",
            "list_id": 1169225,
            "expected_issues": ["Possible custom fields", "Different column structure"]
        },
        {
            "name": "Prueba_SEGMENTOS2",
            "url": "https://acumbamail.com/app/list/1169487/subscriber/list/",
            "list_id": 1169487,
            "expected_issues": ["May have different field names", "Possible empty list"]
        },
        {
            "name": "Lista de Prueba",
            "url": "https://acumbamail.com/app/list/1115559/subscriber/list/",
            "list_id": 1115559,
            "expected_issues": ["Standard test case", "Should work normally"]
        }
    ]

    config = load_config()
    print(f"✅ Config loaded: {len(config)} entries")

    results = []

    with sync_playwright() as p:
        try:
            # Configure browser
            browser = configurar_navegador(p, extraccion_oculta=False)
            context = crear_contexto_navegador(browser, extraccion_oculta=False)
            page = context.new_page()

            print("✅ Browser context created")

            # Login to Acumbamail
            print("🔐 Logging in to Acumbamail...")
            try:
                login(page, context)
                print("✅ Login process completed")
            except Exception as e:
                print(f"⚠️ Login process had issues: {e}")

            # Test each case
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n{'='*20} TEST CASE {i}/{len(test_cases)} {'='*20}")
                print(f"📋 Testing: {test_case['name']}")
                print(f"🔗 URL: {test_case['url']}")
                print(f"🆔 List ID: {test_case['list_id']}")
                print(f"⚠️ Expected issues: {', '.join(test_case['expected_issues'])}")

                result = test_single_segment_case(page, test_case)
                results.append(result)

        except Exception as e:
            print(f"❌ Critical test error: {e}")
            return False
        finally:
            try:
                context.close()
                browser.close()
            except:
                pass

    # Analyze results
    print(f"\n{'='*20} COMPREHENSIVE ANALYSIS {'='*20}")
    analyze_test_results(results)

    return True

def test_single_segment_case(page, test_case):
    """Test a single segment case with error analysis"""
    result = {
        "name": test_case["name"],
        "list_id": test_case["list_id"],
        "success": False,
        "subscribers_count": 0,
        "fields_count": 0,
        "headers_detected": [],
        "errors": [],
        "warnings": [],
        "data_sample": None,
        "performance": {}
    }

    try:
        # Navigate to the list
        print(f"🧭 Navigating to {test_case['name']}...")
        start_time = time.time()

        page.goto(test_case["url"], timeout=45000)
        page.wait_for_load_state("networkidle", timeout=45000)

        navigation_time = time.time() - start_time
        result["performance"]["navigation_time"] = navigation_time

        if navigation_time > 30:
            result["warnings"].append(f"Slow navigation: {navigation_time:.1f}s")

        # Test extraction
        print(f"🧪 Testing extraction...")
        extraction_start = time.time()

        suscriptores = extraer_suscriptores_tabla_lista(page, test_case["name"], test_case["list_id"])

        extraction_time = time.time() - extraction_start
        result["performance"]["extraction_time"] = extraction_time

        # Analyze results
        result["subscribers_count"] = len(suscriptores)

        if suscriptores:
            first_subscriber = suscriptores[0]
            result["fields_count"] = len(first_subscriber.keys())
            result["data_sample"] = dict(list(first_subscriber.items())[:5])  # First 5 fields
            result["success"] = True

            # Check for common issues
            check_data_quality(suscriptores, result)
        else:
            result["errors"].append("No subscribers extracted")

        print(f"📊 Results for {test_case['name']}:")
        print(f"   - Subscribers: {result['subscribers_count']}")
        print(f"   - Fields: {result['fields_count']}")
        print(f"   - Navigation time: {navigation_time:.1f}s")
        print(f"   - Extraction time: {extraction_time:.1f}s")

    except TimeoutError as e:
        error_msg = f"Timeout error: {str(e)}"
        result["errors"].append(error_msg)
        print(f"❌ {error_msg}")
    except Exception as e:
        error_msg = f"Extraction error: {str(e)}"
        result["errors"].append(error_msg)
        print(f"❌ {error_msg}")

    return result

def check_data_quality(suscriptores, result):
    """Check for common data quality issues"""
    emails = [s.get("email", "") for s in suscriptores]

    # Check for duplicates
    unique_emails = set(filter(None, emails))
    if len(emails) != len(unique_emails):
        result["errors"].append(f"Duplicate emails detected: {len(emails)} total, {len(unique_emails)} unique")

    # Check for missing emails
    missing_emails = len([e for e in emails if not e or "@" not in e])
    if missing_emails > 0:
        result["warnings"].append(f"Missing or invalid emails: {missing_emails}")

    # Check for empty fields
    all_fields = set()
    for subscriber in suscriptores:
        all_fields.update(subscriber.keys())

    empty_field_count = {}
    for field in all_fields:
        empty_count = len([s for s in suscriptores if not s.get(field)])
        if empty_count > len(suscriptores) * 0.8:  # More than 80% empty
            empty_field_count[field] = empty_count

    if empty_field_count:
        result["warnings"].append(f"Fields with >80% empty data: {list(empty_field_count.keys())}")

    # Check field mapping issues
    for subscriber in suscriptores[:3]:  # Check first 3
        for field, value in subscriber.items():
            if field != "email" and field != "lista" and value and "@" in str(value):
                result["warnings"].append(f"Possible field mapping issue: '{field}' contains email-like data")
                break

def analyze_test_results(results):
    """Analyze all test results and provide comprehensive report"""
    total_tests = len(results)
    successful_tests = len([r for r in results if r["success"]])

    print(f"📊 OVERALL RESULTS:")
    print(f"   - Total tests: {total_tests}")
    print(f"   - Successful: {successful_tests}")
    print(f"   - Failed: {total_tests - successful_tests}")
    print(f"   - Success rate: {(successful_tests/total_tests)*100:.1f}%")

    print(f"\n🔍 DETAILED ANALYSIS:")
    for result in results:
        print(f"\n📋 {result['name']} (ID: {result['list_id']}):")
        print(f"   ✅ Success: {result['success']}")
        print(f"   📊 Subscribers: {result['subscribers_count']}")
        print(f"   🔧 Fields: {result['fields_count']}")

        if result["performance"]:
            nav_time = result["performance"].get("navigation_time", 0)
            ext_time = result["performance"].get("extraction_time", 0)
            print(f"   ⏱️ Performance: Nav {nav_time:.1f}s, Extract {ext_time:.1f}s")

        if result["errors"]:
            print(f"   ❌ Errors: {len(result['errors'])}")
            for error in result["errors"]:
                print(f"      • {error}")

        if result["warnings"]:
            print(f"   ⚠️ Warnings: {len(result['warnings'])}")
            for warning in result["warnings"]:
                print(f"      • {warning}")

        if result["data_sample"]:
            print(f"   📄 Sample data:")
            for key, value in result["data_sample"].items():
                print(f"      {key}: {value}")

    # Error pattern analysis
    all_errors = []
    all_warnings = []
    for result in results:
        all_errors.extend(result["errors"])
        all_warnings.extend(result["warnings"])

    if all_errors:
        print(f"\n❌ COMMON ERROR PATTERNS:")
        error_types = {}
        for error in all_errors:
            error_type = error.split(":")[0]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        for error_type, count in error_types.items():
            print(f"   • {error_type}: {count} occurrences")

    if all_warnings:
        print(f"\n⚠️ COMMON WARNING PATTERNS:")
        warning_types = {}
        for warning in all_warnings:
            warning_type = warning.split(":")[0]
            warning_types[warning_type] = warning_types.get(warning_type, 0) + 1

        for warning_type, count in warning_types.items():
            print(f"   • {warning_type}: {count} occurrences")

    print(f"\n💡 RECOMMENDATIONS:")
    print("   • Monitor timeout issues for slow networks")
    print("   • Implement field mapping validation")
    print("   • Add duplicate detection and removal")
    print("   • Consider retry mechanisms for failed extractions")
    print("   • Add progress monitoring for large lists")

if __name__ == "__main__":
    import time

    print("🧪 SEGMENT PROCESSING - COMPREHENSIVE ERROR ANALYSIS")
    print("=" * 70)

    success = test_segment_processing_comprehensive()

    if success:
        print("\n✅ COMPREHENSIVE TEST COMPLETED")
        sys.exit(0)
    else:
        print("\n❌ COMPREHENSIVE TEST FAILED")
        sys.exit(1)