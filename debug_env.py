import os
from dotenv import load_dotenv

print("Checking .env file location...")
print(f"Current Directory: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")

load_dotenv(override=True)
key = os.getenv("OPENAI_API_KEY")
print(f"OPENAI_API_KEY found: {key[:5]}...{key[-5:] if key else ''}" if key else "OPENAI_API_KEY NOT FOUND")
