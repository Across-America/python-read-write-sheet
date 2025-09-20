# VAPI Fields Configuration for Smartsheet Integration
# These fields can be directly configured on VAPI website

def get_vapi_customer_fields():
    """
    Get VAPI customer field configuration
    These fields can be used in VAPI customer information
    """
    return {
        "customer_name": "{{customer.variables.customer_name}}",
        "agent_name": "{{customer.variables.agent_name}}", 
        "office": "{{customer.variables.office}}",
        "policy_number": "{{customer.variables.policy_number}}",
        "phone_number": "{{customer.variables.phone_number}}"
    }

def get_vapi_greeting_examples():
    """
    Get VAPI greeting examples
    You can use these variables in VAPI greeting templates
    """
    return {
        "simple_greeting": "Hi {{customer.variables.customer_name}}, this is {{customer.variables.agent_name}} from {{customer.variables.office}} calling about your policy {{customer.variables.policy_number}}.",
        
        "formal_greeting": "Hello {{customer.variables.customer_name}}, this is {{customer.variables.agent_name}} calling from {{customer.variables.office}}. I'm reaching out regarding your insurance policy {{customer.variables.policy_number}}.",
        
        "friendly_greeting": "Hi {{customer.variables.customer_name}}! This is {{customer.variables.agent_name}} from {{customer.variables.office}}. I hope you're doing well. I'm calling about your policy {{customer.variables.policy_number}}."
    }

def print_vapi_setup_instructions():
    """
    Print VAPI setup instructions
    """
    print("=" * 80)
    print("VAPI FIELDS CONFIGURATION GUIDE")
    print("=" * 80)
    
    print("\n📋 Fields to configure on VAPI website:")
    print("-" * 50)
    
    fields = get_vapi_customer_fields()
    for field_name, field_value in fields.items():
        print(f"• {field_name}: {field_value}")
    
    print(f"\n💬 Greeting template examples:")
    print("-" * 50)
    
    greetings = get_vapi_greeting_examples()
    for greeting_name, greeting_text in greetings.items():
        print(f"\n{greeting_name}:")
        print(f"  {greeting_text}")
    
    print(f"\n🔧 VAPI website configuration steps:")
    print("-" * 50)
    print("1. Login to your VAPI account")
    print("2. Edit your Assistant")
    print("3. Add the following fields in Customer Information section:")
    print("   - customer_name: Customer name (客户姓名)")
    print("   - agent_name: Agent name (代理人姓名)") 
    print("   - office: Office location (办公室)")
    print("   - policy_number: Policy number (保单号)")
    print("   - phone_number: Phone number (电话号码)")
    print("4. Use these variables in your Greeting template:")
    print("   Example: Hi {{customer.variables.customer_name}}, ...")
    print("5. Save configuration")
    
    print(f"\n✅ After configuration, your Python code will automatically pass this info to VAPI")
    print("   When you call make_vapi_call(), customer info will be automatically filled into these fields")

if __name__ == "__main__":
    print_vapi_setup_instructions()
