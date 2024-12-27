from langchain_core.runnables import RunnableLambda
from langserve import add_routes

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

from core.server_settings import server_settings


class EncryptRunnable:
    def __init__(self):
        pass

    def encrypt(self, req: str) -> str:
        key = server_settings.secret_key.encode('utf-8')
        cipher = AES.new(key, AES.MODE_ECB)
        encrypted = cipher.encrypt(pad(req.encode('utf-8'), AES.block_size))
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, req: str) -> str:
        return req

    def register(self, app):
        add_routes(app,
                   RunnableLambda(self.encrypt).with_types(input_type=str, output_type=str),
                   path='/encrypt')
        add_routes(app,
                   RunnableLambda(self.decrypt).with_types(input_type=str, output_type=str),
                   path='/decrypt')
