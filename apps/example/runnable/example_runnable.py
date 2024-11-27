from apps.example.user_types.example import ExampleUserType
from langchain_core.runnables import RunnableLambda


class ExampleRunnable:
    def __init__(self):
        pass

    def execute(self, req: ExampleUserType) -> str:
        return req.msg

    def instance(self):
        instance = RunnableLambda(self.execute).with_types(input_type=ExampleUserType, output_type=str)
        return instance
