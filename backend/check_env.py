import os
from dotenv import load_dotenv

load_dotenv()
pk = os.getenv("TIGER_PRIVATE_KEY")
if not pk:
    print("No private key found.")
else:
    print(f"Starts with: {pk[:30]}")
    print(f"Ends with: {pk[-30:]}")
    print(f"Length: {len(pk)}")
    print(f"Number of literal newlines: {pk.count('\n')}")
    print(f"Number of escaped newlines: {pk.count('\\n')}")
