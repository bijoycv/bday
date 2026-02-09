import re

def check_tags(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # regex for all relevant tags, including potential multi-line ones
    # We'll search for {% ... %}
    # We'll use a regex that matches across newlines
    tags = re.finditer(r'\{\%\s*(if|endif|for|endfor|block|endblock|elif|else)\b.*?\%\}', content, re.DOTALL)
    
    stack = []
    
    # To track line numbers, we convert index to line number
    def get_line_num(pos):
        return content.count('\n', 0, pos) + 1

    for match in tags:
        full_tag = match.group(0)
        tag_type = match.group(1)
        line_num = get_line_num(match.start())
        print(f"Found tag: {tag_type} at line {line_num}")
        
        if tag_type in ['if', 'for', 'block']:
            stack.append((tag_type, line_num, full_tag))
        elif tag_type == 'elif' or tag_type == 'else':
            if not stack or stack[-1][0] != 'if':
                print(f"Error: {tag_type} at line {line_num} outside of an 'if' block")
        elif tag_type.startswith('end'):
            expected = tag_type[3:]
            if not stack:
                print(f"Error: Found {tag_type} at line {line_num} but stack is empty. Tag: {full_tag}")
            else:
                last_tag, last_line, _ = stack.pop()
                if last_tag != expected:
                    print(f"Error: Found {tag_type} at line {line_num} but expected end{last_tag} (from line {last_line})")
    
    while stack:
        tag, line, full = stack.pop()
        print(f"Error: Unclosed {tag} from line {line}. Tag: {full}")

if __name__ == "__main__":
    check_tags("dummy_test.html")
