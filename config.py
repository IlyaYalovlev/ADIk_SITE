import os

from dotenv import load_dotenv

load_dotenv()


EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
DATABASE_URL = os.environ.get("DATABASE_URL")
SECRET = os.environ.get("SECRET")
API_KEY = os.environ.get("API_KEY")
