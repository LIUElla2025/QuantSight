import re

env_content = ""
with open('.env', 'r') as f:
    env_content = f.read()

match = re.search(r'TIGER_PRIVATE_KEY=\s*\"?(.*?)\"?\s*(?:\n|$)', env_content, re.DOTALL)
if match:
    pk_str = match.group(1).replace('-----BEGIN RSA PRIVATE KEY-----', '').replace('-----END RSA PRIVATE KEY-----', '').strip()
    print("Found key in env:", len(pk_str))
