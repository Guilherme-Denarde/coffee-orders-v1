import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("firebase_credentials.json")  # Update with your credentials
firebase_admin.initialize_app(cred)

# Firestore database instance
db = firestore.client()
