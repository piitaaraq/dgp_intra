# dgp_intra/routes/lunch/__init__.py
from flask import Blueprint, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from datetime import datetime, time as time_cls
from dgp_intra.extensions import db
from dgp_intra.models import (
    LunchRegistration,
    CreditTransaction, TxType, TxStatus
)

bp = Blueprint("lunch", __name__, url_prefix="/lunch")

def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def _is_locked(reg_date, today, now):
    # locked if in the past, or same-day after 09:00
    if reg_date < today:
        return True
    return reg_date == today and now >= time_cls(9, 0)

def _post_spend(user_id: int, delta: int, reg_date, note: str):
    """
    Write a posted ledger entry for lunch spend/refund.
    delta: -1 for spend, +1 for refund
    """
    tx = CreditTransaction(
        user_id=user_id,
        created_at=datetime.utcnow(),
        posted_at=datetime.utcnow(),
        delta_credits=delta,
        tx_type=TxType.SPEND if delta < 0 else TxType.REFUND,
        status=TxStatus.POSTED,
        amount_dkk_ore=None,  # optional; you only track credits here
        source=f"lunch:{reg_date.isoformat()}",
        created_by_id=user_id,
        note=note,
    )
    db.session.add(tx)

@bp.route("/register/<date>", methods=["POST"])
@login_required
def register(date):
    reg_date = _parse_date(date)
    if not reg_date:
        abort(400)

    today = datetime.today().date()
    now = datetime.now().time()

    if _is_locked(reg_date, today, now):
        flash("Registrering er lukket for i dag (efter kl. 9).")
        return redirect(url_for('dashboard.view'))

    # Already registered?
    existing = LunchRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()
    if existing:
        flash("Allerede tilmeldt den dag.")
        return redirect(url_for('dashboard.view'))

    # Wednesday is free (weekday 2)
    is_free = (reg_date.weekday() == 2)

    # Need credit if not free
    if not is_free and current_user.credit < 1:
        flash("Ikke nok klip.")
        return redirect(url_for('dashboard.view'))

    # Create registration
    reg = LunchRegistration(date=reg_date, user_id=current_user.id)
    db.session.add(reg)

    # Adjust credit + write ledger
    if not is_free:
        current_user.credit -= 1
        _post_spend(
            user_id=current_user.id,
            delta=-1,
            reg_date=reg_date,
            note=f"Frokost {reg_date.strftime('%d/%m')}",
        )

    db.session.commit()
    flash(f"Tilmeldt frokost {reg_date.strftime('%A %d/%m')}")
    return redirect(url_for('dashboard.view'))

@bp.route("/plus-one/<date>", methods=["POST"])
@login_required
def plus_one(date):
    reg_date = _parse_date(date)
    if not reg_date:
        abort(400)

    today = datetime.today().date()
    now = datetime.now().time()

    if _is_locked(reg_date, today, now):
        flash("Du kan ikke tilføje ekstra frokost efter kl. 9.")
        return redirect(url_for('dashboard.view'))

    is_free = (reg_date.weekday() == 2)
    if not is_free and current_user.credit < 1:
        flash("Ikke nok klip til +1.")
        return redirect(url_for('dashboard.view'))

    # “+1” is simply another registration row
    plus = LunchRegistration(date=reg_date, user_id=current_user.id)
    db.session.add(plus)

    if not is_free:
        current_user.credit -= 1
        _post_spend(
            user_id=current_user.id,
            delta=-1,
            reg_date=reg_date,
            note=f"+1 frokost {reg_date.strftime('%d/%m')}",
        )

    db.session.commit()
    flash(f"Tilføjet +1 til {reg_date.strftime('%A %d/%m')}")
    return redirect(url_for('dashboard.view'))

@bp.route("/cancel/<date>", methods=["POST"])
@login_required
def cancel(date):
    reg_date = _parse_date(date)
    if not reg_date:
        abort(400)

    today = datetime.today().date()
    now = datetime.now().time()

    if _is_locked(reg_date, today, now):
        flash("Du kan ikke afmelde efter kl. 9.")
        return redirect(url_for('dashboard.view'))

    registration = LunchRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()
    if not registration:
        flash("Du er ikke tilmeldt den dag.")
        return redirect(url_for('dashboard.view'))

    db.session.delete(registration)

    is_free = (reg_date.weekday() == 2)
    if not is_free:
        # Refund a clip and record REFUND
        current_user.credit += 1
        _post_spend(
            user_id=current_user.id,
            delta=+1,
            reg_date=reg_date,
            note=f"Afmeldt frokost {reg_date.strftime('%d/%m')}",
        )

    db.session.commit()
    flash(f"Din tilmelding til {reg_date.strftime('%A %d/%m')} er annulleret.")
    return redirect(url_for('dashboard.view'))
