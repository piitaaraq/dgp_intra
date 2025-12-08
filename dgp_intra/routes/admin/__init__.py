# dgp_intra/routes/admin/__init__.py
from flask import Blueprint, request, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from dgp_intra.extensions import db
from dgp_intra.models import User, LunchRegistration, WeeklyMenu, BreakfastRegistration, PatientsMenu
from dgp_intra.models import CreditTransaction, TxType, TxStatus
from dgp_intra.utils.menu_extraction import extract_patients_menu_from_docx
from datetime import date, timedelta, datetime
from collections import defaultdict
from urllib.parse import urlparse, urljoin
from werkzeug.utils import secure_filename
import os

bp = Blueprint("admin", __name__, url_prefix="/admin")

def _is_safe_url(target):
    host_url = request.host_url
    test_url = urljoin(host_url, target)
    return urlparse(test_url).scheme in ('http', 'https') and urlparse(host_url).netloc == urlparse(test_url).netloc


@bp.route("/")
@login_required
def dashboard():
    if not current_user.is_admin:
        abort(403)

    users_who_owe = User.query.filter(User.owes > 0).all()

    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    friday_date = start_of_week + timedelta(days=4)

    breakfast_regs = (
        db.session.query(BreakfastRegistration, User)
        .join(User, BreakfastRegistration.user_id == User.id)
        .filter(BreakfastRegistration.date == friday_date)
        .order_by(User.name)
        .all()
    )
    breakfast_users = [u for (_br, u) in breakfast_regs]
    breakfast_count = len(breakfast_users)

    raw_regs = (
        db.session.query(LunchRegistration, User)
        .join(User, LunchRegistration.user_id == User.id)
        .filter(LunchRegistration.date.between(start_of_week, end_of_week))
        .order_by(LunchRegistration.date)
        .all()
    )

    grouped = defaultdict(list)
    for reg, user in raw_regs:
        grouped[reg.date].append(user)

    return render_template(
        'admin_dashboard.html',
        users_who_owe=users_who_owe,
        registrations=raw_regs,
        grouped_registrations=grouped,
        breakfast_users=breakfast_users,
        breakfast_count=breakfast_count,
        breakfast_date=friday_date
    )


@bp.route("/mark_paid/<int:user_id>", methods=["POST"])
@login_required
def mark_paid(user_id):
    if not current_user.is_admin:
        abort(403)

    user = User.query.get(user_id)
    if not user:
        flash("Bruger ikke fundet.")
        return redirect(url_for('admin.dashboard'))

    # 1) Clear the user's debt (as before)
    user.owes = 0

    # 2) Flip all pending PURCHASE transactions to POSTED and timestamp them
    now = datetime.utcnow()
    pending_purchases = (
        CreditTransaction.query
        .filter(
            CreditTransaction.user_id == user.id,
            CreditTransaction.tx_type == TxType.PURCHASE,
            CreditTransaction.status == TxStatus.PENDING
        )
        .all()
    )
    for tx in pending_purchases:
        tx.status = TxStatus.POSTED
        tx.posted_at = now
        # (delta_credits already granted at purchase time; we only change status)

    db.session.commit()
    flash(f"{user.name} er markeret som betalt. ({len(pending_purchases)} køb bogført)")
    return redirect(url_for('admin.dashboard'))


@bp.route("/menu", methods=["GET", "POST"])
@login_required
def menu_input():
    if not current_user.is_admin:
        abort(403)
    
    current_week = date.today().strftime("%Y-W%V")
    week_display = f"Uge {date.today().strftime('%V')}"
    
    # Fetch both menus
    weekly_menu = WeeklyMenu.query.filter_by(week=current_week).first()
    patients_menu = PatientsMenu.query.filter_by(week=current_week).first()
    
    if request.method == 'POST':
        menu_type = request.form.get('menu_type')
        
        if menu_type == 'weekly':
            if not weekly_menu:
                weekly_menu = WeeklyMenu(week=current_week)
            weekly_menu.monday = request.form.get('monday')
            weekly_menu.tuesday = request.form.get('tuesday')
            weekly_menu.wednesday = request.form.get('wednesday')
            weekly_menu.thursday = request.form.get('thursday')
            weekly_menu.friday = request.form.get('friday')
            db.session.add(weekly_menu)
            flash("Personale menu gemt for denne uge.", "success")
        
        elif menu_type == 'patients':
            if not patients_menu:
                patients_menu = PatientsMenu(week=current_week)
            # Lunch
            patients_menu.monday = request.form.get('patients_monday')
            patients_menu.tuesday = request.form.get('patients_tuesday')
            patients_menu.wednesday = request.form.get('patients_wednesday')
            patients_menu.thursday = request.form.get('patients_thursday')
            patients_menu.friday = request.form.get('patients_friday')
            patients_menu.saturday = request.form.get('patients_saturday')
            patients_menu.sunday = request.form.get('patients_sunday')
            patients_menu.monday_dinner = request.form.get('patients_monday_dinner')
            patients_menu.tuesday_dinner = request.form.get('patients_tuesday_dinner')
            patients_menu.wednesday_dinner = request.form.get('patients_wednesday_dinner')
            patients_menu.thursday_dinner = request.form.get('patients_thursday_dinner')
            patients_menu.friday_dinner = request.form.get('patients_friday_dinner')
            patients_menu.saturday_dinner = request.form.get('patients_saturday_dinner')
            patients_menu.sunday_dinner = request.form.get('patients_sunday_dinner')
            db.session.add(patients_menu)
            flash("Patient menu gemt for denne uge.", "success")
        
        db.session.commit()
        
        next_url = request.form.get('next') or url_for('admin.menu_input')
        if not _is_safe_url(next_url):
            next_url = url_for('admin.menu_input')
        return redirect(next_url)
    
    return render_template(
        "admin_menu.html", 
        weekly_menu=weekly_menu,
        patients_menu=patients_menu,
        current_week=week_display
    )


@bp.route("/menu/upload", methods=["POST"])
@login_required
def upload_patients_menu():
    """Upload patient menu from Word document."""
    if not current_user.is_admin:
        abort(403)
    
    if 'menu_file' not in request.files:
        flash('Ingen fil valgt', 'error')
        return redirect(url_for('admin.menu_input'))
    
    file = request.files['menu_file']
    
    if file.filename == '':
        flash('Ingen fil valgt', 'error')
        return redirect(url_for('admin.menu_input'))
    
    if not file.filename.endswith('.docx'):
        flash('Kun .docx filer er tilladt', 'error')
        return redirect(url_for('admin.menu_input'))
    
    try:
        # Save temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', filename)
        file.save(temp_path)
        
        # Extract menu data
        menu_data = extract_patients_menu_from_docx(temp_path)
        
        # Clean up temp file
        os.remove(temp_path)
        
        if not menu_data['week_number']:
            flash('Kunne ikke finde ugenummer i dokumentet', 'error')
            return redirect(url_for('admin.menu_input'))
        
        # Calculate the ISO week string for the extracted week number
        # Get current year
        year = date.today().year
        # Create week string
        week_string = f"{year}-W{menu_data['week_number']:02d}"
        
        # Check if menu already exists
        existing_menu = PatientsMenu.query.filter_by(week=week_string).first()
        
        if existing_menu:
            # Update existing menu
            patients_menu = existing_menu
            action = "opdateret"
        else:
            # Create new menu
            patients_menu = PatientsMenu(week=week_string)
            action = "oprettet"
        
        # Map extracted data to database fields
        patients_menu.monday = menu_data['monday']['lunch']
        patients_menu.tuesday = menu_data['tuesday']['lunch']
        patients_menu.wednesday = menu_data['wednesday']['lunch']
        patients_menu.thursday = menu_data['thursday']['lunch']
        patients_menu.friday = menu_data['friday']['lunch']
        patients_menu.saturday = menu_data['saturday']['lunch']
        patients_menu.sunday = menu_data['sunday']['lunch']
        
        patients_menu.monday_dinner = menu_data['monday']['dinner']
        patients_menu.tuesday_dinner = menu_data['tuesday']['dinner']
        patients_menu.wednesday_dinner = menu_data['wednesday']['dinner']
        patients_menu.thursday_dinner = menu_data['thursday']['dinner']
        patients_menu.friday_dinner = menu_data['friday']['dinner']
        patients_menu.saturday_dinner = menu_data['saturday']['dinner']
        patients_menu.sunday_dinner = menu_data['sunday']['dinner']
        
        db.session.add(patients_menu)
        db.session.commit()
        
        flash(f'Patient menu for uge {menu_data["week_number"]} {action} succesfuldt!', 'success')
        return redirect(url_for('admin.menu_input'))
        
    except Exception as e:
        flash(f'Fejl ved behandling af fil: {str(e)}', 'error')
        return redirect(url_for('admin.menu_input'))