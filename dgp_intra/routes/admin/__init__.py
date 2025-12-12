# dgp_intra/routes/admin/__init__.py
from flask import Blueprint, request, render_template, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user
from dgp_intra.extensions import db
from dgp_intra.models import User, UserRole, Room, LunchRegistration, WeeklyMenu, BreakfastRegistration, PatientsMenu
from dgp_intra.models import CreditTransaction, TxType, TxStatus
from dgp_intra.utils.menu_extraction import extract_patients_menu_from_docx
from dgp_intra.utils.menu_generator import generate_from_patients_menu_model
from datetime import date, timedelta, datetime
from collections import defaultdict
from urllib.parse import urlparse, urljoin
import tempfile
from werkzeug.utils import secure_filename
import os

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _is_safe_url(target):
    host_url = request.host_url
    test_url = urljoin(host_url, target)
    return urlparse(test_url).scheme in ('http', 'https') and urlparse(host_url).netloc == urlparse(test_url).netloc


@bp.before_request
@login_required
def require_admin_access():
    """
    Require appropriate access for admin routes.
    - Menu routes: Kitchen staff or admin
    - All other routes: Admin only
    """
    # Check if this is a menu-related route
    is_menu_route = request.endpoint and 'menu' in request.endpoint
    
    if is_menu_route:
        # Allow kitchen staff and admins for menu routes
        if not (current_user.is_admin or current_user.is_kitchen_staff):
            abort(403)
    else:
        # Require admin for all other routes
        if not (current_user.is_admin or current_user.is_admin_role):
            abort(403)

# Replace the dashboard route in dgp_intra/routes/admin/__init__.py

@bp.route("/")
def dashboard():
    """Admin dashboard with user management and system overview"""
    # Admin-only route - handled by before_request
    
    # Get all users
    all_users = User.query.order_by(User.name).all()
    
    # System statistics
    total_users = len(all_users)
    users_by_role = {}
    for role in UserRole:
        users_by_role[role.value] = sum(1 for u in all_users if u.role == role)
    
    # Get users who owe money
    users_who_owe = User.query.filter(User.owes > 0).order_by(User.owes.desc()).all()
    total_owed = sum(u.owes for u in users_who_owe)
    
    # Room statistics
    from dgp_intra.models import Room
    rooms = Room.query.all()
    total_rooms = len(rooms)
    occupied_rooms = sum(1 for r in rooms if r.is_occupied)
    rooms_need_cleaning = sum(1 for r in rooms if r.needs_cleaning)
    
    # Recent activity (last 10 credit transactions)
    from dgp_intra.models import CreditTransaction
    recent_transactions = (
        CreditTransaction.query
        .order_by(CreditTransaction.created_at.desc())
        .limit(10)
        .all()
    )
    
    return render_template(
        'admin/dashboard.html',
        all_users=all_users,
        total_users=total_users,
        users_by_role=users_by_role,
        users_who_owe=users_who_owe,
        total_owed=total_owed,
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        rooms_need_cleaning=rooms_need_cleaning,
        recent_transactions=recent_transactions
    )


@bp.route("/user/<int:user_id>/edit-role", methods=["POST"])
def edit_user_role(user_id):
    """Change a user's role"""
    # Admin-only route - handled by before_request
    
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in [r.value for r in UserRole]:
        flash('Ugyldig rolle', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Convert string to enum
    user.role = UserRole(new_role)
    db.session.commit()
    
    flash(f'{user.name}s rolle opdateret til {user.role_display}', 'success')
    return redirect(url_for('admin.dashboard'))


@bp.route("/user/<int:user_id>/toggle-admin", methods=["POST"])
def toggle_admin(user_id):
    """Toggle user's is_admin flag (for backward compatibility)"""
    # Admin-only route - handled by before_request
    
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = "aktiveret" if user.is_admin else "deaktiveret"
    flash(f'Admin adgang {status} for {user.name}', 'success')
    return redirect(url_for('admin.dashboard'))


@bp.route("/user/<int:user_id>/reset-password", methods=["POST"])
def reset_user_password(user_id):
    """Reset a user's password"""
    # Admin-only route - handled by before_request
    
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    
    if not new_password or len(new_password) < 6:
        flash('Adgangskode skal være mindst 6 tegn', 'error')
        return redirect(url_for('admin.dashboard'))
    
    from werkzeug.security import generate_password_hash
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash(f'Adgangskode nulstillet for {user.name}', 'success')
    return redirect(url_for('admin.dashboard'))


@bp.route("/user/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    """Delete a user (careful!)"""
    # Admin-only route - handled by before_request
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('Du kan ikke slette dig selv', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Prevent deleting other admins
    if user.is_admin or user.role == UserRole.ADMIN:
        flash('Du kan ikke slette andre administratorer', 'error')
        return redirect(url_for('admin.dashboard'))
    
    user_name = user.name
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Bruger {user_name} slettet', 'success')
    return redirect(url_for('admin.dashboard'))


@bp.route("/user/create", methods=["POST"])
def create_user():
    """Create a new user"""
    # Admin-only route - handled by before_request
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role', 'staff')
    
    if not name or not email or not password:
        flash('Alle felter er påkrævet', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email allerede i brug', 'error')
        return redirect(url_for('admin.dashboard'))
    
    from werkzeug.security import generate_password_hash
    
    new_user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role=UserRole(role)
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    flash(f'Bruger {name} oprettet', 'success')
    return redirect(url_for('admin.dashboard'))

@bp.route("/mark_paid/<int:user_id>", methods=["POST"])
def mark_paid(user_id):
    # Admin-only route - handled by before_request
    user = User.query.get(user_id)
    if not user:
        flash("Bruger ikke fundet.")
        return redirect(url_for('admin.dashboard'))

    # 1) Clear the user's debt
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

    db.session.commit()
    flash(f"{user.name} er markeret som betalt. ({len(pending_purchases)} køb bogført)")
    return redirect(url_for('admin.dashboard'))


@bp.route("/menu", methods=["GET", "POST"])
def menu_input():
    # Kitchen staff allowed - handled by before_request
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
def upload_patients_menu():
    """Upload patient menu from Word document."""
    # Kitchen staff allowed - handled by before_request
    
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
        year = date.today().year
        week_string = f"{year}-W{menu_data['week_number']:02d}"
        
        # Check if menu already exists
        existing_menu = PatientsMenu.query.filter_by(week=week_string).first()
        
        if existing_menu:
            patients_menu = existing_menu
            action = "opdateret"
        else:
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


@bp.route("/menu/download/<week_string>")
def download_patients_menu(week_string):
    """Download patient menu as Word document."""
    # Kitchen staff allowed - handled by before_request
    
    # Fetch the menu
    patients_menu = PatientsMenu.query.filter_by(week=week_string).first()
    
    if not patients_menu:
        flash('Menu ikke fundet', 'error')
        return redirect(url_for('admin.menu_input'))
    
    # Get color from query parameter, default to blue
    base_color = request.args.get('color', '4472C4')
    base_color = base_color.lstrip('#')
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
            temp_path = tmp.name
        
        # Generate the document with custom color
        generate_from_patients_menu_model(patients_menu, temp_path, base_color)
        
        # Extract week number for filename
        week_number = week_string.split('-W')[1]
        filename = f"Patientmenu_Uge_{week_number}.docx"
        
        # Send file and clean up
        response = send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        # Schedule cleanup after sending
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(temp_path)
            except:
                pass
        
        return response
        
    except Exception as e:
        flash(f'Fejl ved generering af dokument: {str(e)}', 'error')
        return redirect(url_for('admin.menu_input'))