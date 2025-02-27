import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("../example.json") 
    firebase_admin.initialize_app(cred)

db = firestore.client()
