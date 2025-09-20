#!/usr/bin/env python3
"""
Apply summary truncation fix to auto_call_and_update.py
Change summary truncation from 150 characters to 80 characters
"""

import re

def apply_summary_fix():
    """Apply the summary truncation fix"""
    
    # Read the current file
    with open('auto_call_and_update.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the summary truncation line
    old_pattern = r'summary_short = summary\[:150\] \+ "\.\.\." if len\(summary\) > 150 else summary'
    new_pattern = r'summary_short = summary[:80] + "..." if len(summary) > 80 else summary'
    
    # Also update the comment
    old_comment = r'# Add summary if available \(truncated\)'
    new_comment = r'# Add summary if available (truncated to fit Smartsheet cell)'
    
    # Apply the changes
    content = re.sub(old_pattern, new_pattern, content)
    content = re.sub(old_comment, new_comment, content)
    
    # Write the modified content back
    with open('auto_call_and_update.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully applied summary truncation fix!")
    print("📝 Changed summary truncation from 150 to 80 characters")
    print("💡 This will make Call Result more concise in Smartsheet")

if __name__ == "__main__":
    apply_summary_fix()
