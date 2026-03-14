import re
with open('.env', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('TIGER_PRIVATE_KEY'):
        # Extract everything between quotes or equal sign
        if '"' in line:
            pk = line.split('"')[1]
        else:
            pk = line.split('=')[1].strip()
        
        # Clean up any trailing == or artifacts
        pk = re.sub(r'([^=]+==).*', r'\1', pk)
        
        # Format properly as a continuous string without quotes
        new_lines.append(f'TIGER_PRIVATE_KEY={pk}\n')
    else:
        new_lines.append(line)

with open('.env', 'w') as f:
    f.writelines(new_lines)
