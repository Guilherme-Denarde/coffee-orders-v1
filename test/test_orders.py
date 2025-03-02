import unittest
import requests
import json
import os
import subprocess
import time
from datetime import datetime

# Base URL for the API - adjust as needed
API_BASE_URL = " https://coffee-orders-43801498060.us-central1.run.app"

class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate auth token before all tests
        cls.auth_token = cls.get_gcp_token()
        
        # Setup test data
        cls.test_product = {
            "nome": f"Test Product {datetime.now().isoformat()}",
            "preco": 29.99,
            "descricao": "Test product description",
            "categoria": "test-category",
            "estoque": 100,
            "codigo": "TEST-SKU-123"
        }
        
        cls.test_order = {
            "cliente": f"Test Customer {datetime.now().isoformat()}",
            "email": "test@example.com",
            "itens": []  # Will be populated after creating test products
        }
        
        # Setup tracking for created resources to clean up later
        cls.created_product_ids = []
        cls.created_order_ids = []
    
    @classmethod
    def tearDownClass(cls):
        # Clean up created resources
        headers = {"Authorization": f"Bearer {cls.auth_token}"}
        
        # Delete test orders
        for order_id in cls.created_order_ids:
            try:
                requests.delete(f"{API_BASE_URL}/pedidos/{order_id}", headers=headers)
            except Exception as e:
                print(f"Failed to delete order {order_id}: {e}")
        
        # Delete test products
        for product_id in cls.created_product_ids:
            try:
                requests.delete(f"{API_BASE_URL}/produtos/{product_id}", headers=headers)
            except Exception as e:
                print(f"Failed to delete product {product_id}: {e}")
    
    @staticmethod
    def get_gcp_token():
        """Generate a GCP identity token for authentication"""
        try:
            # Run gcloud command and capture output
            result = subprocess.run(
                ["gcloud", "auth", "print-identity-token"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error generating GCP token: {e}")
            print(f"Error output: {e.stderr}")
            raise Exception("Failed to generate authentication token")
    
    def refresh_token_if_needed(self):
        """Refresh token if it might be expired"""
        # Tokens typically last 1 hour, but we'll refresh more often to be safe
        self.__class__.auth_token = self.__class__.get_gcp_token()  