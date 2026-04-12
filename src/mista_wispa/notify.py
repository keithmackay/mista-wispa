# src/mista_wispa/notify.py
import rumps


def notify(title: str, message: str, *, subtitle: str = ""):
    rumps.notification(
        title=title,
        subtitle=subtitle,
        message=message,
        sound=False,
    )
