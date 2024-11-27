from apps.kube_service.runnable.pilot_runnable import PilotRunnable


def register_routes(app):
    PilotRunnable().register(app)
