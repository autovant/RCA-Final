"""Check where Settings class definition ends."""
import ast

with open('core/config.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "Settings":
        print(f"Settings class starts at line {node.lineno}")
        print(f"Settings class ends at line {node.end_lineno}")
        print(f"\nClass body has {len(node.body)} statements")
        print("\nLast 5 statements in class body:")
        for stmt in node.body[-5:]:
            print(f"  Line {stmt.lineno}-{stmt.end_lineno}: {ast.unparse(stmt)[:80]}...")
