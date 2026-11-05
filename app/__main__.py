from dotenv import load_dotenv

from app.ui import launch

if __name__ == "__main__":
    load_dotenv(override=True)
    launch()
