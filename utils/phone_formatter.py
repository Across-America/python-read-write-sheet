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
    """
    # Remove any spaces, dashes, or parentheses
    cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    if not cleaned.startswith('+'):
        if len(cleaned) == 10:
            formatted_phone = f"+1{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            formatted_phone = f"+{cleaned}"
        else:
            formatted_phone = f"+1{cleaned}"
    else:
        formatted_phone = cleaned
    
    return formatted_phone
