import json
from urllib import error, request

from django.conf import settings


def initialize_chapa_payment(*, amount, currency, email, first_name, last_name, tx_ref, callback_url, return_url, phone_number=None):
    endpoint = f"{settings.CHAPA_BASE_URL.rstrip('/')}/v1/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "amount": str(amount),
        "currency": currency,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": tx_ref,
        "callback_url": callback_url,
        "return_url": return_url,
    }
    if phone_number:
        payload["phone_number"] = phone_number

    request_body = json.dumps(payload).encode("utf-8")
    req = request.Request(endpoint, data=request_body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        # Read the response body to get the actual error message from Chapa
        try:
            body = exc.read().decode("utf-8")
            detail = json.loads(body)
        except Exception:
            detail = exc.reason
        raise RuntimeError(f"Chapa initialize failed: HTTP {exc.code} - {detail}") from exc
    except (error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Chapa initialize failed: {exc}") from exc


def verify_chapa_payment(tx_ref):
    endpoint = f"{settings.CHAPA_BASE_URL.rstrip('/')}/v1/transaction/verify/{tx_ref}"
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
    }
    req = request.Request(endpoint, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            detail = json.loads(body)
        except Exception:
            detail = exc.reason
        raise RuntimeError(f"Chapa verify failed: HTTP {exc.code} - {detail}") from exc
    except (error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Chapa verify failed: {exc}") from exc
