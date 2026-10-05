"""Merge partial custom-field updates with a record's current values.

Harvest v3 PATCH endpoints replace a record's ``custom_fields`` collection wholesale, so
sending only the field being changed would clear every other custom field. Tools call
``merged_custom_fields`` to send the full list: current values, overlaid with the update.
"""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


def _normalize(entry: dict[str, Any]) -> dict[str, Any]:
    """Accept v1-style ``{id, value}`` and return v3 ``{custom_field_id|name_key, value}``."""
    out = dict(entry)
    if "custom_field_id" not in out and "name_key" not in out and "id" in out:
        out["custom_field_id"] = out.pop("id")
    return out


def merge_with_current(
    current: dict[str, Any] | None,
    updates: list[dict[str, Any]],
    key_for_id: dict[int, str],
) -> list[dict[str, Any]]:
    """Current values (as returned by v3: ``{name_key: {name, type, value}}``) overlaid
    with ``updates``. Current values are sent back exactly as v3 returned them."""
    merged: dict[str, dict[str, Any]] = {}
    for name_key, field in (current or {}).items():
        if isinstance(field, dict) and field.get("value") is not None:
            merged[name_key] = {"name_key": name_key, "value": field["value"]}
    for raw in updates:
        entry = _normalize(raw)
        key = entry.get("name_key") or key_for_id.get(entry.get("custom_field_id"))  # type: ignore[arg-type]
        if key:
            merged[key] = {"name_key": key, "value": entry.get("value")}
        else:
            merged[f"id:{entry.get('custom_field_id')}"] = entry
    return list(merged.values())


async def merged_custom_fields(
    client: GreenhouseClient,
    endpoint: str,
    record_id: int,
    updates: list[dict[str, Any]],
) -> list[dict[str, Any]] | dict[str, Any]:
    """Full custom_fields list for a PATCH of ``endpoint`` record ``record_id``.

    Returns an error dict (and the caller must not write) if the current record or the
    custom field definitions can't be read — writing a partial list would wipe values.
    """
    record = await client.harvest_get_by_id(endpoint, record_id)
    if client._is_error(record):
        return record
    normalized = [_normalize(u) for u in updates]
    ids = [
        u["custom_field_id"] for u in normalized if "name_key" not in u and "custom_field_id" in u
    ]
    key_for_id: dict[int, str] = {}
    if ids:
        fields = await client.harvest_get_ids("/custom_fields", "ids", ids)
        if client._is_error(fields):
            return fields
        key_for_id = {f["id"]: f["name_key"] for f in fields["items"] if f.get("name_key")}
    return merge_with_current(record.get("custom_fields"), normalized, key_for_id)
