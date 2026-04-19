import logging
import platform

logger = logging.getLogger(__name__)


def send_notification(title: str, message: str):
    """
    Sends a native OS notification.
    Currently only supports Windows in Phase 1 as per user request.
    """
    current_os = platform.system()

    if current_os != "Windows":
        logger.info(f"Notification skipped (Non-Windows OS: {current_os}): {title} - {message}")
        return

    try:
        from plyer import notification

        notification.notify(title=title, message=message, app_name="LogicHive", timeout=10)
        logger.info(f"Windows notification sent: {title}")
    except ImportError:
        logger.warning("plyer not installed. Cannot send Windows notification.")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
