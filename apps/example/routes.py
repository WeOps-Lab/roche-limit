from langserve import add_routes

from apps.example.runnable.example_runnable import ExampleRunnable


def register_routes(app):
    add_routes(app, ExampleRunnable().instance(), path='/example')
