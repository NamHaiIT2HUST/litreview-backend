import sys, ast
sys.path.insert(0, '.')

print('Testing syntax of routes.py...')
try:
    with open('src/api/routes.py', 'r', encoding='utf-8') as f:
        src = f.read()
    ast.parse(src)
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')

print()
print('Testing FastAPI app import...')
try:
    from src.main import app
    print('FastAPI app OK')
    routes = [r.path for r in app.routes]
    print(f'Routes count: {len(routes)}')
    for r in routes:
        if 'workspace' in r or 'synthesis' in r:
            print(f'  {r}')
except Exception as e:
    import traceback
    print(f'FAIL: {e}')
    traceback.print_exc()
