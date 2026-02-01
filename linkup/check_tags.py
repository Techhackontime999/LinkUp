import re

def check_tags(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # Find all tags
    tags = re.findall(r'{%\s*(\w+).*?%}', content, re.DOTALL)
    
    stack = []
    for tag in tags:
        if tag in ['if', 'for', 'block']:
            stack.append(tag)
        elif tag == 'endif':
            if not stack or stack[-1] != 'if':
                print(f"Error: endif found but expected {stack[-1] if stack else 'nothing'}")
            else:
                stack.pop()
        elif tag == 'endfor':
            if not stack or stack[-1] != 'for':
                print(f"Error: endfor found but expected {stack[-1] if stack else 'nothing'}")
            else:
                stack.pop()
        elif tag == 'endblock':
            if not stack or stack[-1] != 'block':
                print(f"Error: endblock found but expected {stack[-1] if stack else 'nothing'}")
            else:
                stack.pop()
        elif tag == 'empty':
            if not stack or stack[-1] != 'for':
                print(f"Error: empty found but current stack is {stack}")
    
    if stack:
        print(f"Error: unclosed tags: {stack}")
    else:
        print("All tags are balanced!")

check_tags('templates/base.html')
