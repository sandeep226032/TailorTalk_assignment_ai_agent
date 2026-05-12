import requests
from dataclasses import dataclass

@dataclass
class APIClient:
    base_url: str

    def send_message(self, session_id: str, message: str) -> str:
        try:
            res = requests.post(
                f"{self.base_url}/chat",
                json={"session_id": session_id, "message": message},
                timeout=120,
            )
            res.raise_for_status()
            return res.json()["response"]
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to backend."
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def clear_session(self, session_id: str):
        try:
            requests.post(
                f"{self.base_url}/chat/clear",
                json={"session_id": session_id},
                timeout=5,
            )
        except Exception:
            pass