from app.extensions import login_manager


@login_manager.user_loader
def load_user(user_id):
    """Placeholder etapu 1 — podłączony do modelu User w etapie 2/4."""
    return None
