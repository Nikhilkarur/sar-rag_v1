import os
import glob

models_dir = os.path.join(os.path.dirname(__file__), 'app', 'models')
for filepath in glob.glob(os.path.join(models_dir, '*.py')):
    with open(filepath, 'r') as f:
        content = f.read()
        
    if 'TIMESTAMPTZ' in content:
        # replace import
        content = content.replace('from sqlalchemy.dialects.postgresql import UUID, TEXT, TIMESTAMPTZ, JSONB', 'from sqlalchemy.dialects.postgresql import UUID, TEXT, JSONB\nfrom sqlalchemy import DateTime')
        content = content.replace('from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ, JSONB', 'from sqlalchemy.dialects.postgresql import UUID, JSONB\nfrom sqlalchemy import DateTime')
        content = content.replace('from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ', 'from sqlalchemy.dialects.postgresql import UUID\nfrom sqlalchemy import DateTime')
        content = content.replace('from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ, JSONB, TEXT', 'from sqlalchemy.dialects.postgresql import UUID, JSONB, TEXT\nfrom sqlalchemy import DateTime')
        content = content.replace('from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ, TEXT', 'from sqlalchemy.dialects.postgresql import UUID, TEXT\nfrom sqlalchemy import DateTime')
        
        # replace usage
        content = content.replace('TIMESTAMPTZ', 'DateTime(timezone=True)')
        
        with open(filepath, 'w') as f:
            f.write(content)
print("Models fixed.")
