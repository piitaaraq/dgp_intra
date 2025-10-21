# dgp_intra/routes/credit/__init__.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func, or_
from dgp_intra.extensions import db
from dgp_intra.models import CreditTransaction, TxType, TxStatus

bp = Blueprint("credit", __name__, url_prefix="/credit")

# -------------------------
# Purchase / coupon
# -------------------------

def _process_purchase(amount: int, success_redirect):
    if amount not in [1, 5]:
        flash("Ugyldigt antal klip valgt.")
        return redirect(success_redirect)

    cost = amount * 22
    user = db.session.merge(current_user)

    if user.owes >= 110:
        flash("Du skylder allerede 110 kr. Du kan ikke købe flere klip før du har betalt.")
        return redirect(url_for('credit.ledger'))
    if user.owes + cost > 110:
        flash("Denne transaktion vil få din gæld til at overstige 110 kr. Køb færre klip eller betal først.")
        return redirect(url_for('credit.ledger'))

    # Business rule (unchanged): user gets clips immediately, debt increases
    user.credit += amount
    user.owes += cost

    # Ledger rule (NEW): create a PURCHASE as "Ikke bogført" (pending payment).
    # This shows up in the ledger right away but marked as not posted yet.
    tx = CreditTransaction(
        user_id=user.id,
        created_at=datetime.utcnow(),
        posted_at=None,                 # not posted yet
        delta_credits=amount,           # +credits granted now
        tx_type=TxType.PURCHASE,
        status=TxStatus.PENDING,        # <- Ikke bogført indtil køkkenet markerer betalt
        amount_dkk_ore=cost * 100,      # øre
        source="purchase:web",
        created_by_id=user.id,
        note=f"Køb af {amount} klip (DKK {cost})",
    )
    db.session.add(tx)

    db.session.commit()
    flash(f"Du har købt {amount} klip. Du skylder nu {user.owes} DKK.")
    # You can send them to the ledger to see the 'Ikke bogført' entry immediately:
    return redirect(url_for('credit.ledger'))

@bp.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        amount = int(request.form.get('amount'))
        return _process_purchase(amount, url_for('credit.buy'))
    return render_template('buy_credits.html')

@bp.route("/coupon", methods=["GET", "POST"])
@login_required
def coupon():
    if request.method == "POST":
        amount = int(request.form.get('amount'))
        return _process_purchase(amount, url_for('credit.coupon'))
    return render_template('buy_coupon.html')


# -------------------------
# Ledger
# -------------------------

def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        return None

@bp.route("/ledger", methods=["GET"])
@login_required
def ledger():
    # Filters
    f_type   = request.args.get("type")      # purchase/spend/adjustment/refund
    f_status = request.args.get("status")    # pending/posted/canceled
    f_from   = _parse_date(request.args.get("from"))
    f_to     = _parse_date(request.args.get("to"))
    qtext    = (request.args.get("q") or "").strip()

    q = CreditTransaction.query.filter(CreditTransaction.user_id == current_user.id)

    if f_type:
        try:
            q = q.filter(CreditTransaction.tx_type == TxType(f_type))
        except ValueError:
            pass
    if f_status:
        try:
            q = q.filter(CreditTransaction.status == TxStatus(f_status))
        except ValueError:
            pass
    if f_from:
        q = q.filter(CreditTransaction.created_at >= f_from)
    if f_to:
        end_of = f_to.replace(hour=23, minute=59, second=59, microsecond=999999)
        q = q.filter(CreditTransaction.created_at <= end_of)
    if qtext:
        like = f"%{qtext}%"
        q = q.filter(or_(CreditTransaction.source.ilike(like),
                         CreditTransaction.note.ilike(like)))

    # Pagination
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except Exception:
        page = 1
    per_page = 20
    pagination = q.order_by(CreditTransaction.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    items = pagination.items

    # Totals (credits-based)
    posted_balance = (
        db.session.query(func.coalesce(func.sum(CreditTransaction.delta_credits), 0))
        .filter(
            CreditTransaction.user_id == current_user.id,
            CreditTransaction.status == TxStatus.POSTED,
        )
        .scalar()
    )
    pending_delta = (
        db.session.query(func.coalesce(func.sum(CreditTransaction.delta_credits), 0))
        .filter(
            CreditTransaction.user_id == current_user.id,
            CreditTransaction.status == TxStatus.PENDING,
        )
        .scalar()
    )

    return render_template(
        "ledger.html",
        items=items,
        pagination=pagination,
        TxType=TxType,
        TxStatus=TxStatus,
        posted_balance=posted_balance,
        pending_delta=pending_delta,
        f_type=f_type,
        f_status=f_status,
        f_from=request.args.get("from", ""),
        f_to=request.args.get("to", ""),
        qtext=qtext,
    )
