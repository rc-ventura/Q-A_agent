import os

from dotenv import load_dotenv

load_dotenv(override=True)
os.environ.setdefault("OPENAI_API_KEY", "sk-unit-test-sem-rede")
