from langchain_core.runnables import RunnableLambda
from langserve import add_routes

from apps.auto_mate.user_types.encrypt import EncryptUserType, DecryptUserType
from apps.auto_mate.utils.entrypt import encrypt_data, decrypt_data
from core.server_settings import server_settings


class EncryptRunnable:

    def encrypt(self, req: EncryptUserType) -> str:
        return encrypt_data(req.content, req.key.encode('utf-8'))

    def decrypt(self, req: DecryptUserType) -> str:
        return decrypt_data(req.content, req.key.encode('utf-8'))

    def register(self, app):
        add_routes(app,
                   RunnableLambda(self.encrypt).with_types(input_type=EncryptUserType, output_type=str),
                   path='/encrypt')
        add_routes(app,
                   RunnableLambda(self.decrypt).with_types(input_type=DecryptUserType, output_type=str),
                   path='/decrypt')
