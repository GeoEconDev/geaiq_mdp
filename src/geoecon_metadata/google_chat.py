from typing import Dict, Any, List
import logging
import requests
import os
from urllib.parse import urlparse
from getpass import getuser


def obtener_nombre_archivo(url):
    ruta = urlparse(url).path
    return os.path.basename(ruta)


class GoogleChatBot:
    def __init__(self, webhook_url: str, email: str | None = None):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)
        # If you still need credentials for other GCP services, keep this:
        self.session = requests.Session()  # Use a session for better performance
        self.email = email or os.getenv("USER_EMAIL") or os.getenv("USER") or getuser() or os.getlogin() or "Unknown"

    def send_message(
        self, message: str, thread_key: str = None, widgets: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            message_data: Dict[str, Any] = {"text": message}

            if widgets:
                message_data["cards"] = widgets

            if thread_key:
                # Webhooks don't directly support threads in the same way the API does.
                # You'll need to handle threading logic yourself if needed (e.g., using a separate system to track messages by thread_key).
                self.logger.warning(
                    "Thread keys are not directly supported with webhooks.  You must implement threading logic yourself."
                )

            response = self.session.post(self.webhook_url, json=message_data)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            self.logger.info(f"Message sent successfully: {response.json()}")
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error sending message to Google Chat webhook: {e}")
            if response.status_code != 200:
                self.logger.error(
                    f"Response content: {response.text}"
                )  # Log the content of the error
            raise  # Re-raise the exception for handling upstream
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            raise

    def send_message_with_url(
        self, title: str, message: str, url: str, thread_key: str = None
    ) -> Dict[str, Any]:
        widgets = [
            {
                "header": {
                    "title": title,
                    "subtitle": "Haz clic en el botón para más información",
                },
                "sections": [
                    {
                        "widgets": [
                            {"textParagraph": {"text": message}},
                            {
                                "buttons": [
                                    {
                                        "textButton": {
                                            "text": "Abrir Enlace",
                                            "onClick": {"openLink": {"url": url}},
                                        }
                                    }
                                ]
                            },
                        ]
                    }
                ],
            }
        ]
        return self.send_message(
            "", thread_key, widgets
        )  # Message can be empty if using widgets

    def send_report_message(
        self,
        title: str,
        message: str,
        report_url: str,
        metadata_urls: list[str],
        thread_key: str = None,
        subtitle: str = None,
    ) -> Dict[str, Any]:
        widgets = [
            {
                "header": {
                    "title": title,
                    "subtitle": subtitle.format(email=self.email)
                    or "Haz click en los botones para más información",
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": message.format(email=self.email)
                                }
                            },
                            {
                                "buttons": [
                                    {
                                        "textButton": {
                                            "text": "Report",
                                            "onClick": {
                                                "openLink": {"url": report_url}
                                            },
                                        }
                                    }
                                ]
                            },
                            {
                                "buttons": [
                                    {
                                        "textButton": {
                                            "text": obtener_nombre_archivo(url),
                                            "onClick": {"openLink": {"url": url}},
                                        }
                                    }
                                    for url in metadata_urls
                                ]
                            },
                        ]
                    }
                ],
            }
        ]
        return self.send_message(
            "", thread_key, widgets
        )  # Message can be empty if using widgets

    def send_start_task_message(
        self,
        title: str,
        logs_url: str,
        metadata_urls: list[str],
        thread_key: str = None,
        subtitle: str = None,
    ) -> Dict[str, Any]:
        widgets = [
            {
                "header": {
                    "title": title,
                    "subtitle": subtitle.format(email=self.email)
                    or "Haz click en los botones para más información",
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "buttons": [
                                    {
                                        "textButton": {
                                            "text": "🪵 Logs",
                                            "onClick": {"openLink": {"url": logs_url}},
                                        }
                                    }
                                ]
                            },
                            {
                                "buttons": [
                                    {
                                        "textButton": {
                                            "text": f"📂 {obtener_nombre_archivo(url)}",
                                            "onClick": {"openLink": {"url": url}},
                                        }
                                    }
                                    for url in metadata_urls
                                ]
                            },
                        ]
                    }
                ],
            }
        ]
        return self.send_message(
            "", thread_key, widgets
        )  # Message can be empty if using widgets

    def send_simple_message(
        self, message: str, thread_key: str = None
    ) -> Dict[str, Any]:
        return self.send_message(message, thread_key)

    def send_message_with_widgets(
        self, message: str, widgets: list[Dict[str, Any]], thread_key: str = None
    ) -> Dict[str, Any]:
        return self.send_message(
            message, thread_key, widgets
        )  # Corrected: Include thread_key
