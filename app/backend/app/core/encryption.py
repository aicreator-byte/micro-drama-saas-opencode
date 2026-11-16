from cryptography.fernet import Fernet
import base64
from app.core.config import settings


class EncryptionService:
    def __init__(self):
        # Generate a valid Fernet key from the settings key
        key = settings.ENCRYPTION_KEY.encode()
        # Pad or truncate to 32 bytes, then base64 encode
        key = (key + b'0' * 32)[:32]
        self.fernet = Fernet(base64.urlsafe_b64encode(key))
    
    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.fernet.decrypt(encrypted_data.encode()).decode()


encryption_service = EncryptionService()