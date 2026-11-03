"""Work out cycle day, phase and length from recorded period days.

The cycle form used to ask for all three. That is three numbers a player has
to work out herself, every single day, and getting them wrong quietly poisons
the risk model. What she actually knows without counting is whether she has
her period today.

So the app asks only that, and derives the rest here. Two sources feed the
derivation and both are hers:

* what she entered herself (``CycleEntry.menstrual_flow``)
* what a device reported, but only for providers she switched cycle sync on
  for (``WearableDaily.menstrual_flow``)

Her own entry wins where both exist - she knows better than the ring.

The arithmetic itself lives in ``app.services.wearables.cycle`` and is shared
with the device suggestions, so both paths cannot drift apart.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CycleEntry, WearableDaily
from app.services.wearables.cycle import CycleEstimate
from app.services.wearables.cycle import estimate as estimate_from_flow

# Two cycles of context is enough to place a day and to learn her rhythm,
# without dragging a year of history into every save.
HISTORY_DAYS = 400


def flow_history(db: Session, *, player_id: int, until: date) -> dict[date, str]:
    """Every day she is known to have bled, from both sources.

    Device days are laid down first and her own entries written over them, so
    a manual correction always wins.
    """
    since = until - timedelta(days=HISTORY_DAYS)
    history: dict[date, str] = {}

    for row_date, flow in db.execute(
        select(WearableDaily.date, WearableDaily.menstrual_flow).where(
            WearableDaily.player_id == player_id,
            WearableDaily.menstrual_flow.is_not(None),
            WearableDaily.date <= until,
            WearableDaily.date >= since,
        )
    ).tuples():
        if flow:
            history[row_date] = flow

    for row_date, flow in db.execute(
        select(CycleEntry.date, CycleEntry.menstrual_flow).where(
            CycleEntry.player_id == player_id,
            CycleEntry.menstrual_flow.is_not(None),
            CycleEntry.date <= until,
            CycleEntry.date >= since,
        )
    ).tuples():
        if flow:
            history[row_date] = flow

    return history


def estimate_for(
    db: Session, *, player_id: int, day: date, flow: str | None = None
) -> CycleEstimate | None:
    """Cycle day, phase and length for ``day``, or None without a basis.

    ``flow`` is the value being entered right now, before it is stored. The
    first day of a period is exactly the day that defines cycle day 1, and
    without this it would be judged on a history that does not contain it yet.
    """
    history = flow_history(db, player_id=player_id, until=day)
    if flow is not None:
        history[day] = flow
    return estimate_from_flow(history, on=day)


def fill_in(db: Session, *, player_id: int, payload: dict) -> dict:
    """Complete a cycle entry with what can be derived.

    Only ever fills blanks: anything the player typed stays exactly as she
    typed it. A guess must never overwrite a statement.
    """
    needed = ("cycle_day", "phase", "cycle_length")
    if all(payload.get(field) is not None for field in needed):
        return payload

    estimate = estimate_for(
        db,
        player_id=player_id,
        day=payload["date"],
        flow=payload.get("menstrual_flow"),
    )
    if estimate is None:
        return payload

    filled = dict(payload)
    if filled.get("cycle_day") is None:
        filled["cycle_day"] = estimate.cycle_day
    if filled.get("phase") is None:
        filled["phase"] = estimate.phase
    if filled.get("cycle_length") is None:
        filled["cycle_length"] = estimate.cycle_length
    return filled
