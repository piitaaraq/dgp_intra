from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from datetime import datetime
from dgp_intra.extensions import db
from dgp_intra.models import CreditTransaction, TxType, TxStatus, User
from .vipps import VippsClient, VippsAPIError
import uuid

bp = Blueprint("klippekort", __name__, url_prefix="/klippekort")


@bp.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    """Shopping cart - select amount of clips to purchase"""
    if request.method == "POST":
        try:
            amount = int(request.form.get('amount'))
            if amount not in [1, 5]:
                flash("Ugyldigt antal klip valgt.", "error")
                return redirect(url_for('klippekort.cart'))
            
            return redirect(url_for('klippekort.initiate', amount=amount))
        except ValueError:
            flash("Ugyldigt antal klip.", "error")
    
    price_per_clip = current_app.config.get('KLIPPEKORT_PRICE_PER_CLIP', 24)
    
    return render_template('klippekort/cart.html', price_per_clip=price_per_clip)


@bp.route("/initiate/<int:amount>")
@login_required
def initiate(amount):
    """Initiate payment with Vipps MobilePay"""
    if amount not in [1, 5]:
        flash("Ugyldigt antal klip.", "error")
        return redirect(url_for('klippekort.cart'))
    
    price_per_clip = current_app.config.get('KLIPPEKORT_PRICE_PER_CLIP', 24)
    total_dkk = amount * price_per_clip
    
    # Generate unique reference
    reference = f"dgp-{current_user.id}-{uuid.uuid4().hex[:8]}"
    
    # Create pending transaction in our database
    user = db.session.merge(current_user)
    tx = CreditTransaction(
        user_id=user.id,
        created_at=datetime.utcnow(),
        posted_at=None,
        delta_credits=0,  # Will be granted after capture
        tx_type=TxType.PURCHASE,
        status=TxStatus.PENDING,
        amount_dkk_ore=total_dkk * 100,
        source=f"mobilepay:{reference}",
        created_by_id=user.id,
        note=f"MobilePay køb af {amount} klip - venter på betaling",
    )
    db.session.add(tx)
    db.session.commit()
    
    # Create payment with Vipps
    try:
        client = VippsClient()
        result = client.create_payment(
            reference=reference,
            amount_dkk=total_dkk,
            description=f"{amount} klip til madordning",
            return_url=url_for('klippekort.callback', _external=True),
            phone=None  # Could add user phone if stored
        )
        
        # Redirect user to payment page
        return redirect(result['redirectUrl'])
    
    except VippsAPIError as e:
        current_app.logger.error(f"Vipps API error: {e}")
        flash("Der opstod en fejl ved oprettelse af betaling. Prøv igen senere.", "error")
        
        # Mark transaction as failed
        tx.status = TxStatus.CANCELED
        tx.note = f"Fejl ved oprettelse: {str(e)}"
        db.session.commit()
        
        return redirect(url_for('klippekort.cart'))


@bp.route("/callback")
@login_required
def callback():
    """User returns here after MobilePay"""
    
    # Find the most recent PENDING MobilePay transaction for this user
    tx = CreditTransaction.query.filter_by(
        user_id=current_user.id,
        status=TxStatus.PENDING
    ).filter(
        CreditTransaction.source.like('mobilepay:%')
    ).order_by(
        CreditTransaction.created_at.desc()
    ).first()
    
    if not tx:
        flash("Kunne ikke finde din betaling. Prøv venligst igen.", "error")
        return redirect(url_for('klippekort.cart'))
    
    # Extract reference from source (format: "mobilepay:dgp-1-abc123")
    reference = tx.source.split(':', 1)[1]
    
    # Redirect to processing page WITH reference
    return redirect(url_for('klippekort.processing', ref=reference))


@bp.route("/processing")
@login_required
def processing():
    """Shows processing page - JavaScript will poll for status"""
    reference = request.args.get('ref')
    if not reference:
        flash("Manglende betalingsreference.", "error")
        return redirect(url_for('klippekort.cart'))
    
    return render_template('klippekort/processing.html')


@bp.route("/status/<reference>")
@login_required
def status(reference):
    """
    AJAX endpoint to check payment status
    Returns JSON with current state
    """
    try:
        client = VippsClient()
        payment = client.get_payment(reference)
        
        state = payment['state']
        
        if state == 'AUTHORIZED':
            # Payment authorized - capture it!
            try:
                client.capture_payment(reference)
                
                # Find our transaction
                tx = CreditTransaction.query.filter_by(
                    source=f"mobilepay:{reference}"
                ).first()
                
                if tx:
                    # Grant credits
                    user = db.session.get(User, tx.user_id)
                    
                    # Calculate amount from transaction
                    amount_dkk = tx.amount_dkk_ore / 100
                    clips = int(amount_dkk / current_app.config.get('KLIPPEKORT_PRICE_PER_CLIP', 24))
                    
                    user.credit += clips
                    tx.delta_credits = clips
                    tx.status = TxStatus.POSTED
                    tx.posted_at = datetime.utcnow()
                    tx.note = f"MobilePay betaling gennemført - {clips} klip"
                    
                    db.session.commit()
                    
                    return {
                        'status': 'success',
                        'message': f'Betaling gennemført! Du har fået {clips} klip.',
                        'redirect': url_for('klippekort.success')
                    }
            
            except Exception as e:
                current_app.logger.error(f"Error capturing payment: {e}")
                return {'status': 'error', 'message': 'Fejl ved gennemførelse'}
        
        elif state == 'ABORTED':
            return {
                'status': 'cancelled',
                'message': 'Betaling annulleret',
                'redirect': url_for('klippekort.cart')
            }
        
        elif state == 'CREATED':
            return {'status': 'pending', 'message': 'Venter på godkendelse...'}
        
        else:
            return {'status': 'unknown', 'message': f'Ukendt status: {state}'}
    
    except VippsAPIError as e:
        return {'status': 'error', 'message': 'Kunne ikke hente status'}


@bp.route("/success")
@login_required
def success():
    """Success page after payment"""
    return render_template('klippekort/success.html', user=current_user)