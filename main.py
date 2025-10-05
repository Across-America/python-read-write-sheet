#!/usr/bin/env python3
"""
VAPI Batch Call System - Main Entry Point
Modular batch calling system for insurance customer outreach
"""

from workflows import (
    test_single_customer_call,
    test_batch_call_not_called,
    show_not_called_customers
)


def display_menu():
    """Display main menu"""
    print("\n🤖 BATCH CALL TEST SYSTEM")
    print("=" * 50)
    print("Testing batch calling for 'Not call yet' customers")
    print("Using Spencer: Call Transfer V2 Campaign assistant")
    print("=" * 50)
    print("\nSelect test mode:")
    print("1. Test single customer call")
    print("2. Test batch call for all 'Not call yet' customers")
    print("3. Just show customers (no calling)")
    print("4. Exit")


def main():
    """Main entry point"""
    while True:
        display_menu()
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            print("\n" + "=" * 60)
            test_single_customer_call()
        elif choice == "2":
            print("\n" + "=" * 60)
            test_batch_call_not_called()
        elif choice == "3":
            print("\n" + "=" * 60)
            show_not_called_customers()
        elif choice == "4":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4")
        
        print("\n" + "-" * 60)
        input("Press Enter to continue...")


if __name__ == "__main__":
    main()
