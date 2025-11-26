"""
Vipps MobilePay API client
Works with both mock and production APIs
"""
import requests
from flask import current_app
import uuid


class VippsAPIError(Exception):
    """Raised when Vipps API returns an error"""
    pass


class VippsClient:
    """Client for Vipps MobilePay ePayment API"""
    
    def __init__(self):
        self.base_url = current_app.config['VIPPS_API_BASE_URL']
        self.client_id = current_app.config['VIPPS_CLIENT_ID']
        self.client_secret = current_app.config['VIPPS_CLIENT_SECRET']
        self.subscription_key = current_app.config['VIPPS_SUBSCRIPTION_KEY']
        self.msn = current_app.config['VIPPS_MSN']
        self._access_token = None
    
    def _get_token(self):
        """Get access token (cached for this request)"""
        if self._access_token:
            return self._access_token
        
        url = f"{self.base_url}/accesstoken/get"
        headers = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Merchant-Serial-Number': self.msn,
        }
        
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        
        self._access_token = response.json()['access_token']
        return self._access_token
    
    def _make_request(self, method, endpoint, json=None):
        """Make authenticated request to Vipps API"""
        token = self._get_token()
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Merchant-Serial-Number': self.msn,
            'Content-Type': 'application/json',
        }
        
        response = requests.request(method, url, headers=headers, json=json)
        
        if not response.ok:
            raise VippsAPIError(f"Vipps API error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def create_payment(self, reference, amount_dkk, description, return_url, phone=None):
        """
        Create a new payment
        
        Args:
            reference: Unique payment reference (e.g., "order-123")
            amount_dkk: Amount in DKK (will be converted to øre)
            description: Payment description
            return_url: URL to redirect user after payment
            phone: Optional customer phone number
        
        Returns:
            dict with 'reference' and 'redirectUrl'
        """
        amount_ore = int(amount_dkk * 100)  # Convert DKK to øre
        
        payload = {
            "amount": {
                "currency": "DKK",
                "value": amount_ore
            },
            "reference": reference,
            "returnUrl": return_url,
            "paymentDescription": description,
            "userFlow": "WEB_REDIRECT",
            "paymentMethod": {
                "type": "WALLET"
            }
        }
        
        if phone:
            payload["customer"] = {"phoneNumber": phone}
        
        return self._make_request('POST', '/epayment/v1/payments', json=payload)
    
    def get_payment(self, reference):
        """
        Get payment details
        
        Returns:
            dict with payment state and details
        """
        return self._make_request('GET', f'/epayment/v1/payments/{reference}')
    
    def capture_payment(self, reference, amount_dkk=None):
        """
        Capture (finalize) a payment
        
        Args:
            reference: Payment reference
            amount_dkk: Amount to capture (None = full amount)
        """
        payload = {}
        if amount_dkk is not None:
            payload["modificationAmount"] = {
                "currency": "DKK",
                "value": int(amount_dkk * 100)
            }
        
        return self._make_request('POST', f'/epayment/v1/payments/{reference}/capture', json=payload)
    
    def cancel_payment(self, reference):
        """Cancel a payment"""
        return self._make_request('POST', f'/epayment/v1/payments/{reference}/cancel')