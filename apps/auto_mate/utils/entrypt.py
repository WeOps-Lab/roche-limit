import base64
from typing import Union

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


def encrypt_data(data: str, key: bytes) -> str:
    if len(key) not in AES.key_size:
        raise ValueError("Key must be 16, 24, or 32 bytes long.")

    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + encrypted_data).decode('utf-8')


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    if len(key) not in AES.key_size:
        raise ValueError("Key must be 16, 24, or 32 bytes long.")

    encrypted_data_bytes = base64.b64decode(encrypted_data)
    iv = encrypted_data_bytes[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes[AES.block_size:]), AES.block_size)
    return decrypted_data.decode('utf-8')