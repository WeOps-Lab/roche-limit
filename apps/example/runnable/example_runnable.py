from apps.example.user_types.example import ExampleUserType
from langchain_core.runnables import RunnableLambda
from langserve import add_routes


class ExampleRunnable:
    def __init__(self):
        pass

    def example(self, req: ExampleUserType) -> str:
        return req.msg

    def register(self, app):
        add_routes(app,
                   RunnableLambda(self.example).with_types(input_type=ExampleUserType, output_type=str),
                   path='/example')
