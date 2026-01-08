"""
Phone number formatting utilities
"""

def format_phone_number(phone_number):
    """
    Format phone number to E.164 format
    
    Args:
        phone_number (str): Phone number in any format
    
    Returns:
        str: Phone number in E.164 format (e.g., +19093100491)
    
    Examples:
        >>> format_phone_number("(909) 310-0491")
        '+19093100491'
        >>> format_phone_number("9093100491")
        '+19093100491'
        >>> format_phone_number("+1 909 310 0491")
        '+19093100491'
        >>> format_phone_number("+52 867 740 1381")
        '+528677401381'
    """
    if not phone_number:
        return phone_number
    
    # Convert to string if not already
    phone_str = str(phone_number).strip()
    
    if not phone_str:
        return phone_str
    
    # Remove any spaces, dashes, parentheses, and other common separators
    cleaned = phone_str.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("/", "")
    
    # Remove any non-digit characters except the leading +
    if cleaned.startswith('+'):
        # Keep the + and remove any non-digit characters after it
        digits_only = ''.join(c for c in cleaned[1:] if c.isdigit())
        cleaned = '+' + digits_only
    else:
        # Remove any non-digit characters
        cleaned = ''.join(c for c in cleaned if c.isdigit())
    
    # If already starts with +, validate and return
    if cleaned.startswith('+'):
        # Ensure it's a valid E.164 format (at least +1 for US, or other country codes)
        if len(cleaned) >= 8:  # Minimum: +1 + 10 digits = 12 chars, but allow shorter for other countries
            return cleaned
        else:
            # If too short, might be invalid - try to fix
            if len(cleaned) > 1:
                # Remove the + and treat as regular number
                cleaned = cleaned[1:]
            else:
                return phone_str  # Return original if can't parse
    
    # Handle numbers without country code
    if not cleaned.startswith('+'):
        if len(cleaned) == 10:
            # 10-digit US number - add +1
            formatted_phone = f"+1{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            # 11-digit number starting with 1 - add +
            formatted_phone = f"+{cleaned}"
        elif len(cleaned) == 9:
            # 9-digit number - might be missing leading 1, add +1
            # This handles cases like "552-752-9867" which becomes "5527529867"
            formatted_phone = f"+1{cleaned}"
        elif len(cleaned) > 0:
            # Other length - assume US and add +1
            formatted_phone = f"+1{cleaned}"
        else:
            # Empty or invalid - return original
            return phone_str
    else:
        formatted_phone = cleaned
    
    # Final validation: ensure it starts with + and has at least 10 digits after country code
    if formatted_phone.startswith('+'):
        digits_after_plus = ''.join(c for c in formatted_phone[1:] if c.isdigit())
        if len(digits_after_plus) < 10:
            # Too short - might be invalid, but return it anyway (let VAPI validate)
            pass
    
    return formatted_phone
