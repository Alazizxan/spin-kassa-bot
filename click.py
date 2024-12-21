import requests
import hashlib
import time

def generate_auth_header(merchant_user_id, secret_key):
    """
    Generate the Auth header required for API requests.
    """
    timestamp = str(int(time.time()))
    digest = hashlib.sha1((timestamp + secret_key).encode()).hexdigest()
    auth_header = f"{merchant_user_id}:{digest}:{timestamp}"
    return auth_header

def create_card_token(service_id, card_number, expire_date, temporary, auth):
    """
    Create a card token.
    """
    url = "https://api.click.uz/v2/merchant/card_token/request"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Auth": auth
    }
    data = {
        "service_id": service_id,
        "card_number": card_number,
        "expire_date": expire_date,
        "temporary": temporary
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

def verify_card_token(service_id, card_token, sms_code, auth):
    """
    Verify a card token.
    """
    url = "https://api.click.uz/v2/merchant/card_token/verify"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Auth": auth
    }
    data = {
        "service_id": service_id,
        "card_token": card_token,
        "sms_code": sms_code
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

def payment_with_token(service_id, card_token, amount, merchant_trans_id, auth):
    """
    Make a payment using a card token.
    """
    url = "https://api.click.uz/v2/merchant/card_token/payment"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Auth": auth
    }
    data = {
        "service_id": service_id,
        "card_token": card_token,
        "amount": amount,
        "transaction_parameter": merchant_trans_id
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

def delete_card_token(service_id, card_token, auth):
    """
    Delete a card token.
    """
    url = f"https://api.click.uz/v2/merchant/card_token/{service_id}/{card_token}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Auth": auth
    }
    response = requests.delete(url, headers=headers)
    return response.json()

