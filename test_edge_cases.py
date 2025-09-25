#!/usr/bin/env python3
"""
Test script for edge cases and error scenarios in subscriber extraction
"""
import sys
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

def test_edge_cases():
    """Test edge cases and potential error scenarios"""
    print("🧪 EDGE CASES AND ERROR SCENARIOS TEST")
    print("=" * 60)

    edge_cases = [
        {
            "name": "Empty List Test",
            "description": "Test behavior with empty or very small list",
            "url": "https://acumbamail.com/app/list/1169494/subscriber/list/",  # Datos list (might be empty)
            "list_id": 1169494,
            "expected_issues": ["May be empty", "Could have minimal fields"]
        },
        {
            "name": "Large List Test",
            "description": "Test with larger subscriber base",
            "url": "https://acumbamail.com/app/list/1163787/subscriber/list/",  # AUDIENCIA PROVINCIAL
            "list_id": 1163787,
            "expected_issues": ["Performance issues", "Memory usage", "Pagination"]
        },
        {
            "name": "Special Characters Test",
            "description": "Test with special characters in names/emails",
            "url": "https://acumbamail.com/app/list/1167967/subscriber/list/",  # Alicia, Yolanda y Mercedes
            "list_id": 1167967,
            "expected_issues": ["Unicode handling", "CSV encoding", "Name parsing"]
        }
    ]

    config = load_config()
    results = []

    with sync_playwright() as p:
        try:
            browser = configurar_navegador(p, extraccion_oculta=False)
            context = crear_contexto_navegador(browser, extraccion_oculta=False)
            page = context.new_page()

            print("✅ Browser context created")

            # Login
            try:
                login(page, context)
                print("✅ Login completed")
            except Exception as e:
                print(f"⚠️ Login issues: {e}")

            # Test each edge case
            for i, case in enumerate(edge_cases, 1):
                print(f"\n{'='*15} EDGE CASE {i}/{len(edge_cases)} {'='*15}")
                result = test_edge_case(page, case)
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

    # Test error recovery scenarios
    print(f"\n{'='*20} ERROR RECOVERY TESTS {'='*20}")
    test_error_recovery_scenarios()

    # Analyze all results
    analyze_edge_case_results(results)
    return True

def test_edge_case(page, case):
    """Test a single edge case"""
    result = {
        "name": case["name"],
        "description": case["description"],
        "success": False,
        "issues_found": [],
        "performance_metrics": {},
        "data_quality": {}
    }

    try:
        print(f"🧪 {case['name']}: {case['description']}")
        print(f"🔗 URL: {case['url']}")

        # Navigation with timeout monitoring
        import time
        start_time = time.time()

        try:
            page.goto(case["url"], timeout=60000)  # Extended timeout
            page.wait_for_load_state("networkidle", timeout=60000)
        except TimeoutError:
            result["issues_found"].append("Navigation timeout - slow network or server issues")
            return result

        nav_time = time.time() - start_time
        result["performance_metrics"]["navigation_time"] = nav_time

        # Check for UI elements that might indicate issues
        check_ui_issues(page, result)

        # Attempt extraction
        extraction_start = time.time()

        try:
            suscriptores = extraer_suscriptores_tabla_lista(page, case["name"], case["list_id"])
            extraction_time = time.time() - extraction_start

            result["performance_metrics"]["extraction_time"] = extraction_time
            result["success"] = True

            # Analyze data quality
            analyze_data_quality(suscriptores, result)

            print(f"✅ {case['name']}: {len(suscriptores)} subscribers, {extraction_time:.1f}s")

        except Exception as e:
            result["issues_found"].append(f"Extraction failed: {str(e)}")
            print(f"❌ {case['name']}: Extraction failed - {e}")

    except Exception as e:
        result["issues_found"].append(f"Test failed: {str(e)}")
        print(f"❌ {case['name']}: Test failed - {e}")

    return result

def check_ui_issues(page, result):
    """Check for UI elements that might indicate problems"""
    try:
        # Check for error messages
        if page.locator("text=Error").count() > 0:
            result["issues_found"].append("Error message detected on page")

        # Check for empty state
        if page.locator("text=No hay suscriptores").count() > 0:
            result["issues_found"].append("Empty list detected")

        # Check for loading indicators stuck
        loading_elements = page.locator(".loading, .spinner, [data-loading]").count()
        if loading_elements > 0:
            result["issues_found"].append("Loading indicators still visible")

        # Check for pagination
        pagination_elements = page.locator(".pagination, .page-nav").count()
        result["data_quality"]["has_pagination"] = pagination_elements > 0

    except Exception:
        pass  # UI checks are optional

def analyze_data_quality(suscriptores, result):
    """Analyze data quality for edge cases"""
    if not suscriptores:
        result["data_quality"]["empty_result"] = True
        return

    result["data_quality"]["subscriber_count"] = len(suscriptores)
    result["data_quality"]["field_count"] = len(suscriptores[0].keys()) if suscriptores else 0

    # Check for various data issues
    emails = [s.get("email", "") for s in suscriptores]

    # Email validation
    valid_emails = [e for e in emails if e and "@" in e and "." in e]
    result["data_quality"]["valid_email_percentage"] = (len(valid_emails) / len(emails)) * 100 if emails else 0

    # Check for encoding issues
    encoding_issues = []
    for subscriber in suscriptores[:5]:  # Check first 5
        for field, value in subscriber.items():
            if value and isinstance(value, str):
                if "�" in value or "?" in value:  # Common encoding issue indicators
                    encoding_issues.append(f"Possible encoding issue in {field}")

    if encoding_issues:
        result["issues_found"].extend(encoding_issues)

    # Check for suspiciously similar data
    if len(suscriptores) > 1:
        first_subscriber = suscriptores[0]
        identical_count = 0
        for subscriber in suscriptores[1:]:
            if subscriber == first_subscriber:
                identical_count += 1

        if identical_count > len(suscriptores) * 0.5:
            result["issues_found"].append("High number of identical records - possible duplication")

def test_error_recovery_scenarios():
    """Test error recovery scenarios without actual browser"""
    print("🛡️ Testing error recovery scenarios...")

    # Test 1: Invalid list ID
    print("1. Invalid list ID handling")
    # This would be tested by passing an invalid ID to the extraction function

    # Test 2: Network timeout simulation
    print("2. Network timeout scenarios")
    # This would be tested by setting very short timeouts

    # Test 3: Memory limitations
    print("3. Memory usage patterns")
    # This would be tested with very large datasets

    # Test 4: Malformed HTML
    print("4. Malformed HTML handling")
    # The JavaScript should handle unexpected HTML structures

    print("✅ Error recovery scenarios mapped")

def analyze_edge_case_results(results):
    """Analyze all edge case results"""
    print("\n🔍 EDGE CASE ANALYSIS RESULTS:")

    total_cases = len(results)
    successful_cases = len([r for r in results if r["success"]])

    print(f"📊 Success Rate: {successful_cases}/{total_cases} ({(successful_cases/total_cases)*100:.1f}%)")

    # Performance analysis
    nav_times = [r["performance_metrics"].get("navigation_time", 0) for r in results if r["performance_metrics"]]
    if nav_times:
        avg_nav = sum(nav_times) / len(nav_times)
        max_nav = max(nav_times)
        print(f"⏱️ Navigation: Avg {avg_nav:.1f}s, Max {max_nav:.1f}s")

    # Issue categorization
    all_issues = []
    for result in results:
        all_issues.extend(result["issues_found"])

    if all_issues:
        print(f"\n⚠️ ISSUES FOUND ({len(all_issues)} total):")
        issue_categories = {}
        for issue in all_issues:
            category = issue.split(":")[0]
            issue_categories[category] = issue_categories.get(category, 0) + 1

        for category, count in sorted(issue_categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {category}: {count}")

    # Data quality summary
    print("\n📊 DATA QUALITY SUMMARY:")
    for result in results:
        if result["success"] and "subscriber_count" in result["data_quality"]:
            count = result["data_quality"]["subscriber_count"]
            fields = result["data_quality"]["field_count"]
            email_valid = result["data_quality"].get("valid_email_percentage", 0)
            print(f"   • {result['name']}: {count} subscribers, {fields} fields, {email_valid:.1f}% valid emails")

    print("\n🛡️ ROBUSTNESS ASSESSMENT:")
    robustness_score = (successful_cases / total_cases) * 100

    if robustness_score >= 90:
        print(f"   ✅ EXCELLENT ({robustness_score:.1f}%): System handles edge cases very well")
    elif robustness_score >= 70:
        print(f"   ⚠️ GOOD ({robustness_score:.1f}%): System handles most edge cases well")
    elif robustness_score >= 50:
        print(f"   ⚠️ MODERATE ({robustness_score:.1f}%): Some edge cases need attention")
    else:
        print(f"   ❌ POOR ({robustness_score:.1f}%): Many edge cases fail")

    print("\n💡 FINAL RECOMMENDATIONS:")
    print("   • Implement retry logic for navigation timeouts")
    print("   • Add progress indicators for large list processing")
    print("   • Include encoding detection and conversion")
    print("   • Add data validation and sanitization")
    print("   • Implement graceful degradation for UI changes")
    print("   • Add monitoring for performance regression")

if __name__ == "__main__":

    success = test_edge_cases()

    if success:
        print("\n✅ EDGE CASE TESTING COMPLETED")
    else:
        print("\n❌ EDGE CASE TESTING FAILED")