from apps.auto_mate.runnable.encrypt_runnable import EncryptRunnable


def register_routes(app):
    EncryptRunnable().register(app)
