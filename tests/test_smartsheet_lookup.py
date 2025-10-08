#!/usr/bin/env python3
"""
Test script for SmartsheetService flexible lookup functionality
Tests backward compatibility and new lookup methods
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import SmartsheetService
from config import CANCELLATION_SHEET_ID


def test_backward_compatibility():
    """Test that existing sheet_id method still works"""
    print("\n" + "=" * 80)
    print("TEST 1: Backward Compatibility (sheet_id)")
    print("=" * 80)

    try:
        service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
        print(f"✅ Service initialized with sheet_id: {service.sheet_id}")

        # Try to get sheet info to confirm it works
        sheet = service.smart.Sheets.get_sheet(service.sheet_id)
        print(f"✅ Sheet found: '{sheet.name}'")
        print(f"   📊 Total rows: {sheet.total_row_count}")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_lookup_by_sheet_name():
    """Test lookup by sheet name only"""
    print("\n" + "=" * 80)
    print("TEST 2: Lookup by Sheet Name")
    print("=" * 80)

    # First, get the actual sheet name from the sheet_id
    try:
        temp_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
        sheet = temp_service.smart.Sheets.get_sheet(CANCELLATION_SHEET_ID)
        sheet_name = sheet.name
        print(f"📋 Using sheet name: '{sheet_name}'")
    except Exception as e:
        print(f"❌ Could not get sheet name: {e}")
        return False

    # Now test lookup by name
    try:
        service = SmartsheetService(sheet_name=sheet_name)
        print(f"✅ Service initialized with sheet_name")
        print(f"   🆔 Found sheet ID: {service.sheet_id}")
        print(f"   ✓ Matches expected ID: {service.sheet_id == CANCELLATION_SHEET_ID}")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_list_all_sheets():
    """Helper: List all accessible sheets"""
    print("\n" + "=" * 80)
    print("HELPER: List All Accessible Sheets")
    print("=" * 80)

    try:
        temp_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
        response = temp_service.smart.Sheets.list_sheets(include_all=True)
        sheets = response.data

        print(f"📊 Found {len(sheets)} accessible sheets:")
        for i, sheet in enumerate(sheets[:10], 1):
            print(f"   {i}. '{sheet.name}' (ID: {sheet.id})")

        if len(sheets) > 10:
            print(f"   ... and {len(sheets) - 10} more")

        return True

    except Exception as e:
        print(f"❌ Failed to list sheets: {e}")
        return False


def test_list_all_workspaces():
    """Helper: List all accessible workspaces"""
    print("\n" + "=" * 80)
    print("HELPER: List All Accessible Workspaces")
    print("=" * 80)

    try:
        temp_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
        response = temp_service.smart.Workspaces.list_workspaces(include_all=True)
        workspaces = response.data

        print(f"📊 Found {len(workspaces)} accessible workspaces:")
        for i, workspace in enumerate(workspaces, 1):
            print(f"   {i}. '{workspace.name}' (ID: {workspace.id})")

        return True

    except Exception as e:
        print(f"❌ Failed to list workspaces: {e}")
        return False


def test_error_handling():
    """Test error handling for invalid inputs"""
    print("\n" + "=" * 80)
    print("TEST 3: Error Handling")
    print("=" * 80)

    # Test 1: No parameters
    print("\n📋 Test 3a: No parameters provided")
    try:
        service = SmartsheetService()
        print("❌ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")

    # Test 2: Non-existent sheet name
    print("\n📋 Test 3b: Non-existent sheet name")
    try:
        service = SmartsheetService(sheet_name="This Sheet Does Not Exist XYZ123")
        print("❌ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")

    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 SMARTSHEET SERVICE LOOKUP TESTS")
    print("=" * 80)

    results = []

    # Test backward compatibility
    results.append(("Backward Compatibility", test_backward_compatibility()))

    # List available sheets (helper)
    test_list_all_sheets()

    # List available workspaces (helper)
    test_list_all_workspaces()

    # Test lookup by name
    results.append(("Lookup by Sheet Name", test_lookup_by_sheet_name()))

    # Test error handling
    results.append(("Error Handling", test_error_handling()))

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")

    return passed == total


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
