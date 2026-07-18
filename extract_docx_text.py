import re
import zipfile
from pathlib import Path

root = Path('dossier')
for path in sorted(root.glob('*.docx')):
    print('FILE', path.name)
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith('document.xml'):
                text = z.read(name).decode('utf-8', errors='ignore')
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                print(text[:3000])
                print('---')
                break
