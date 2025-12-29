import os
from kiteconnect import KiteConnect

def get_kite_client(api_key: str):
    """Factory function to get a Kite client for a specific API key."""
    return KiteConnect(api_key=api_key)

def generate_session(api_key, api_secret, request_token):
    """Generates a session for a specific set of credentials."""
    client = get_kite_client(api_key)
    data = client.generate_session(request_token, api_secret=api_secret)
    return data
