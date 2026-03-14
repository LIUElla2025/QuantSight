import os
import re
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def add_newlines(s, length):
    return '\n'.join(s[i:i+length] for i in range(0, len(s), length))

def try_parse(b64_str):
    b64_str = re.sub(r'\s+', '', b64_str)
    # fix padding
    pad = len(b64_str) % 4
    if pad:
        b64_str += '=' * (4 - pad)
        
    formatted = add_newlines(b64_str, 64)
    for header in ['RSA PRIVATE KEY', 'PRIVATE KEY']:
        pem = f'-----BEGIN {header}-----\n{formatted}\n-----END {header}-----'
        try:
            key = serialization.load_pem_private_key(pem.encode(), password=None, backend=default_backend())
            print(f'SUCCESS with {header}')
            return pem
        except Exception as e:
            pass
    return None

def fix():
    with open('.env', 'r') as f:
        env_content = f.read()

    match = re.search(r'TIGER_PRIVATE_KEY=\s*\"?(.*?)\"?\s*(?:\n|$)', env_content, re.DOTALL)
    if not match:
        print("No match")
        return
        
    pk = match.group(1).replace('-----BEGIN RSA PRIVATE KEY-----', '').replace('-----END RSA PRIVATE KEY-----', '').strip()
    
    parts = pk.split('=Privatekeypk8=') if '=Privatekeypk8=' in pk else [pk]
    
    successful_pem = None
    for part in parts:
        successful_pem = try_parse(part)
        if successful_pem: break
            
    if successful_pem:
        # replace block
        new_env = ''
        lines = env_content.split('\n')
        in_pk = False
        for line in lines:
            if line.startswith('TIGER_PRIVATE_KEY'):
                escaped_pem = successful_pem.replace('\n', '\\n')
                new_env += f'TIGER_PRIVATE_KEY="{escaped_pem}"\n'
                
                # Check if it was a multi-line value without quotes closed on same line
                if '"' in line and line.count('"') < 2:
                    in_pk = True
                elif not '"' in line and not escaped_pem.endswith('KEY-----'):
                    in_pk = True
            elif in_pk:
                if '"' in line or '-----END' in line:
                    in_pk = False
            else:
                new_env += line + '\n'
                
        with open('.env', 'w') as f:
            f.write(new_env.strip() + '\n')
            
        print("Fixed and saved!")
    else:
        print("Could not parse any part.")

if __name__ == '__main__':
    fix()
