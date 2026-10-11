


from .models import Notification


def create_notification(recipient, title, message, report=None):
    """Create a persistent notification for one user."""
    if recipient is None:
        return None

    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        report=report
    )
