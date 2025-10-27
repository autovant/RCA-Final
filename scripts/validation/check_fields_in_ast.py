"""Check if feature flag fields are in the AST."""
import ast

with open('core/config.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "Settings":
        print("Looking for field assignments...")
        
        # Find all assignments in the class
        assignments = [s for s in node.body if isinstance(s, ast.AnnAssign)]
        
        print(f"\nFound {len(assignments)} annotated assignments (fields)")
        
        # Look for our feature flags
        for assign in assignments:
            if hasattr(assign.target, 'id'):
                field_name = assign.target.id
                if 'INCIDENTS' in field_name or 'PLATFORM_DETECTION' in field_name or 'ARCHIVE_EXPANDED' in field_name:
                    print(f"  ✓ Found: {field_name} at line {assign.lineno}")
        
        # Check last few fields
        print("\nLast 10 field definitions:")
        for assign in assignments[-10:]:
            if hasattr(assign.target, 'id'):
                print(f"  Line {assign.lineno}: {assign.target.id}")
