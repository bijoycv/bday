import re

def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # Fix split endif
    # Search for {% endif followed by newline and potentially spaces then %}
    new_content = re.sub(r'\{\%\s*endif\s*\n\s*\%\}', '{% endif %}', content)
    
    if new_content != content:
        print("Fixed split endif tags.")
        with open(filename, 'w') as f:
            f.write(new_content)
    else:
        print("No split endif tags found by regex.")

if __name__ == "__main__":
    fix_file("/Volumes/Playground/My Office Works/Birthday-Wishes/bday/templates/birthday/patient_list.html")
