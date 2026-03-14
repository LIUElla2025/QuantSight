import re

with open('.env', 'r') as f:
    content = f.read()

# Extract the TIGER_PRIVATE_KEY value
import os
from dotenv import dotenv_values
env_vars = dotenv_values(".env")

pk = env_vars.get('TIGER_PRIVATE_KEY', '')

# Remove 'U101...' account numbers or 'license=...' trailing artifacts
# A base64 string shouldn't have 'license=' or 'env='
cleaned = pk
for extra in ['license=TBNZ', 'env=PROD', '\n']:
    cleaned = cleaned.replace(extra, '')

# If it ends with U10... we can regex remove it (Tiger accounts start with U)
cleaned = re.sub(r'U\d+$', '', cleaned.strip())

# Rewrite the .env properly
new_content = ""
for line in content.split('\n'):
    if line.startswith('TIGER_PRIVATE_KEY'):
        new_content += f'TIGER_PRIVATE_KEY="{cleaned}"\n'
    else:
        new_content += line + '\n'

with open('.env', 'w') as f:
    f.write(new_content)

print("Fixed .env")
