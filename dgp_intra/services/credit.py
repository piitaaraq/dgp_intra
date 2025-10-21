from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import with_for_update
from flask_sqlalchemy import SQLAlchemy
from models import CreditTransaction, TxType, TxStatus
from models import User
from extensions import db

def _lock_user_row(user_id: int) -> User:
    # MySQL/MariaDB: SELECT ... FOR UPDATE
    user = db.session.execute(
        select(User).where(User.id == user_id).with_for_update()
    ).scalar_one()
    return user

def post_transaction(tx: CreditTransaction, prevent_negative=True) -> CreditTransaction:
    """
    Move a transaction from PENDING to POSTED and update the user's cached balance.
    Wrap your call in the same DB transaction (session).
    """
    if tx.status != TxStatus.PENDING:
        return tx  # idempotent-ish

    user = _lock_user_row(tx.user_id)

    # If you want to enforce no negatives:
    if prevent_negative and tx.delta_credits < 0:
        projected = (user.credit or 0) + tx.delta_credits
        if projected < 0:
            raise ValueError("Insufficient credit")

    tx.status = TxStatus.POSTED
    tx.posted_at = datetime.utcnow()

    # update cached balance
    user.credit = (user.credit or 0) + tx.delta_credits

    db.session.add_all([tx, user])
    return tx

def create_purchase(user_id: int, credits: int, amount_dkk_ore: int | None = None,
                    note: str | None = None, created_by_id: int | None = None,
                    post_immediately=False) -> CreditTransaction:
    tx = CreditTransaction(
        user_id=user_id,
        delta_credits=credits,
        tx_type=TxType.PURCHASE,
        status=TxStatus.PENDING if not post_immediately else TxStatus.POSTED,
        amount_dkk_ore=amount_dkk_ore,
        note=note,
        created_by_id=created_by_id,
        posted_at=datetime.utcnow() if post_immediately else None,
    )
    db.session.add(tx)

    if post_immediately:
        # Keep cache in sync if we skipped PENDING
        user = _lock_user_row(user_id)
        user.credit = (user.credit or 0) + credits
        db.session.add(user)

    return tx

def charge_for_lunch(user_id: int, date_str: str, created_by_id: int | None = None) -> CreditTransaction:
    tx = CreditTransaction(
        user_id=user_id,
        delta_credits=-1,
        tx_type=TxType.SPEND,
        status=TxStatus.PENDING,
        source=f"lunch:{date_str}",
        created_by_id=created_by_id
    )
    db.session.add(tx)
    post_transaction(tx)  # will lock user and prevent negative by default
    return tx

def cancel_lunch_restore(user_id: int, date_str: str, created_by_id: int | None = None) -> CreditTransaction:
    tx = CreditTransaction(
        user_id=user_id,
        delta_credits=+1,
        tx_type=TxType.REFUND,
        status=TxStatus.PENDING,
        source=f"lunch:{date_str}",
        created_by_id=created_by_id
    )
    db.session.add(tx)
    post_transaction(tx, prevent_negative=False)  # adding credits
    return tx

def adjustment(user_id: int, delta: int, note: str | None = None,
               created_by_id: int | None = None) -> CreditTransaction:
    tx = CreditTransaction(
        user_id=user_id,
        delta_credits=delta,
        tx_type=TxType.ADJUSTMENT,
        status=TxStatus.PENDING,
        note=note,
        created_by_id=created_by_id
    )
    db.session.add(tx)
    post_transaction(tx, prevent_negative=(delta < 0))
    return tx
