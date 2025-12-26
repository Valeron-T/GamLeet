import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY")
ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET")

kite_connect = KiteConnect(api_key=ZERODHA_API_KEY)

def generate_session(request_token):
    data = kite_connect.generate_session(request_token, api_secret=ZERODHA_API_SECRET)
    kite_connect.set_access_token(data["access_token"])
    return data
    # Optionally, save access_token to a secure storage for reuse
