# VAPI Setup Guide for Personalized Calls

This guide shows you how to configure VAPI to use customer information from Smartsheet for personalized greetings.

## Required VAPI Fields

Configure these fields in your VAPI Assistant's Customer Information section:

| Field Name | Variable | Description |
|------------|----------|-------------|
| `customer_name` | `{{customer.variables.customer_name}}` | Customer's name from Smartsheet (客户姓名) |
| `agent_name` | `{{customer.variables.agent_name}}` | Agent's name from Smartsheet (代理人姓名) |
| `office` | `{{customer.variables.office}}` | Office location from Smartsheet (办公室) |
| `policy_number` | `{{customer.variables.policy_number}}` | Policy number from Smartsheet (保单号) |
| `phone_number` | `{{customer.variables.phone_number}}` | Phone number from Smartsheet (电话号码) |

## Greeting Template Examples

Use these templates in your VAPI Greeting section:

### Simple Greeting
```
Hi {{customer.variables.customer_name}}, this is {{customer.variables.agent_name}} from {{customer.variables.office}} calling about your policy {{customer.variables.policy_number}}.
```

### Formal Greeting
```
Hello {{customer.variables.customer_name}}, this is {{customer.variables.agent_name}} calling from {{customer.variables.office}}. I'm reaching out regarding your insurance policy {{customer.variables.policy_number}}.
```

### Friendly Greeting
```
Hi {{customer.variables.customer_name}}! This is {{customer.variables.agent_name}} from {{customer.variables.office}}. I hope you're doing well. I'm calling about your policy {{customer.variables.policy_number}}.
```

## Configuration Steps

1. **Login to VAPI Dashboard**
   - Go to your VAPI account
   - Navigate to your Assistant settings

2. **Configure Customer Fields**
   - Go to Customer Information section
   - Add the 5 fields listed above
   - Use the exact variable names shown

3. **Set Up Greeting Template**
   - Go to Greeting section
   - Choose one of the template examples above
   - Or create your own using the variables

4. **Test Configuration**
   - Save your changes
   - Test with a sample call to verify personalization works

## How It Works

1. Your Python code extracts customer information from Smartsheet
2. The `make_vapi_call()` function passes this data to VAPI
3. VAPI uses the variables in your greeting template
4. The customer receives a personalized call with their name and policy details

## Python Code Integration

The Python code automatically handles:
- Extracting customer data from Smartsheet
- Formatting phone numbers
- Passing customer variables to VAPI
- Error handling for missing data

No additional configuration needed in Python - just use the existing `make_vapi_call()` function with customer information.

## Troubleshooting

- **No personalization**: Check that field names match exactly
- **Missing data**: Verify Smartsheet has the required customer information
- **Wrong format**: Ensure phone numbers are in correct format (+1XXXXXXXXXX)

## Support

If you need help with configuration, check:
1. VAPI documentation for field configuration
2. Smartsheet data structure matches expected format
3. Python code is passing data correctly
