import os
from app import app

# L'extensió no pot impedir que el servidor arrenqui.
try:
    import enhancements
    enhancements.register(app, __import__('app'))
except Exception as exc:
    print(f'WARNING: enhancements no s’han pogut carregar: {exc}', flush=True)

@app.get('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')), debug=False)
