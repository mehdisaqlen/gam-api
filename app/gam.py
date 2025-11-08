# app/gam.py
import os
import time
from typing import Dict, Any, List

from googleads import ad_manager, oauth2

API_VERSION = "v202411"
SCOPE = "https://www.googleapis.com/auth/dfp"

# Network list cache: 24 hours
NETWORK_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
_network_cache: List[dict] | None = None
_network_cache_ts: float | None = None


# --- helpers to read dict-or-object safely ---
def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _results(page) -> list:
    # page can be dict or object; results may be missing
    if page is None:
        return []
    res = _get(page, "results", None)
    return res or []


def _pql_where_text(field: str, value: str) -> Dict[str, Any]:
    return {
        "query": f"WHERE {field} = :val",
        "values": [
            {
                "key": "val",
                "value": {"xsi_type": "TextValue", "value": value},
            }
        ],
    }


# --- client builders ---
def build_client(network_code: str) -> ad_manager.AdManagerClient:
    """
    Build an AdManagerClient scoped to a specific network.
    Assumes the service account is a user in that network with API access.
    """
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "./sa.json")
    app_name = os.environ.get("APP_NAME", "GAM Access API")
    oauth2_client = oauth2.GoogleServiceAccountClient(key_path, SCOPE)
    return ad_manager.AdManagerClient(oauth2_client, app_name, network_code)


def build_client_no_network() -> ad_manager.AdManagerClient:
    """
    Build an AdManagerClient not tied to any single network.
    Used to list all accessible networks.
    """
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "./sa.json")
    app_name = os.environ.get("APP_NAME", "GAM Access API")
    oauth2_client = oauth2.GoogleServiceAccountClient(key_path, SCOPE)
    return ad_manager.AdManagerClient(oauth2_client, app_name)


# --- role + user helpers ---
def get_admin_role_id(client: ad_manager.AdManagerClient) -> int:
    """
    Fetch the 'Administrator' roleId using UserService.getAllRoles().
    """
    user_service = client.GetService("UserService", version=API_VERSION)
    roles = user_service.getAllRoles() or []
    for r in roles:
        if _get(r, "name") == "Administrator":
            rid = _get(r, "id")
            if rid is None:
                break
            return int(rid)
    raise RuntimeError("Administrator role not found in this network.")


def find_user_by_email(client: ad_manager.AdManagerClient, email: str):
    user_service = client.GetService("UserService", version=API_VERSION)
    page = user_service.getUsersByStatement(_pql_where_text("email", email))
    users = _results(page)
    return users[0] if users else None


def create_user_as_admin(
    client: ad_manager.AdManagerClient,
    email: str,
    role_id: int,
):
    user_service = client.GetService("UserService", version=API_VERSION)
    created = user_service.createUsers(
        [
            {
                "name": email.split("@")[0],  # simple default display name
                "email": email,
                "roleId": role_id,
                "isActive": True,
            }
        ]
    ) or []
    return created[0]


def update_user_role(
    client: ad_manager.AdManagerClient,
    user_id: int,
    role_id: int,
):
    user_service = client.GetService("UserService", version=API_VERSION)
    updated = user_service.updateUsers(
        [
            {
                "id": user_id,
                "roleId": role_id,
            }
        ]
    ) or []
    return updated[0]


def grant_admin_for_email(
    client: ad_manager.AdManagerClient,
    email: str,
) -> Dict[str, Any]:
    """
    Idempotent:
      - If user does not exist → create as Administrator.
      - If exists with different role → upgrade to Administrator.
      - If already Administrator → no-op.
    """
    admin_role_id = get_admin_role_id(client)
    existing = find_user_by_email(client, email)

    if not existing:
        created = create_user_as_admin(client, email, admin_role_id)
        return {
            "status": "created",
            "userId": int(_get(created, "id")),
            "roleId": admin_role_id,
        }

    current_role = _get(existing, "roleId")
    if int(current_role) != admin_role_id:
        updated = update_user_role(
            client,
            int(_get(existing, "id")),
            admin_role_id,
        )
        return {
            "status": "upgraded",
            "userId": int(_get(updated, "id")),
            "roleId": admin_role_id,
        }

    return {
        "status": "already-admin",
        "userId": int(_get(existing, "id")),
        "roleId": admin_role_id,
    }


# --- networks listing + cache ---
def _fetch_networks_from_api() -> List[dict]:
    """
    Internal: hit NetworkService.getAllNetworks() and normalize
    to list[{"networkCode", "displayName"}].
    """
    client = build_client_no_network()
    svc = client.GetService("NetworkService", version=API_VERSION)
    networks = svc.getAllNetworks() or []

    result: List[dict] = []
    for n in networks:
        if isinstance(n, dict):
            code = n.get("networkCode")
            name = n.get("displayName")
        else:
            code = getattr(n, "networkCode", None)
            name = getattr(n, "displayName", None)

        if code is not None:
            result.append(
                {
                    "networkCode": str(code),
                    "displayName": name,
                }
            )
    return result


def list_accessible_networks_cached(force_refresh: bool = False) -> List[dict]:
    """
    Return cached networks if still fresh, otherwise call API and refresh cache.

    force_refresh=True bypasses TTL and forces a fresh call to GAM.
    """
    global _network_cache, _network_cache_ts

    now = time.time()
    if (
        not force_refresh
        and _network_cache is not None
        and _network_cache_ts is not None
        and now - _network_cache_ts < NETWORK_CACHE_TTL_SECONDS
    ):
        return _network_cache

    networks = _fetch_networks_from_api()
    _network_cache = networks
    _network_cache_ts = now
    return networks


def list_accessible_networks() -> List[dict]:
    """
    Backwards-compatible helper: return cached networks (no force refresh).
    """
    return list_accessible_networks_cached(force_refresh=False)
