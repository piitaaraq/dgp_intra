# dgp_intra/routes/rooms/__init__.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from dgp_intra.extensions import db
from dgp_intra.models import Room, CleaningLog, CleaningStatus, MealRegistration, MealType
from datetime import datetime, date

bp = Blueprint("rooms", __name__, url_prefix="/rooms")


@bp.route("/")
@login_required
def index():
    """Display room status board for all users"""
    from datetime import timedelta
    from dgp_intra.models import DailyArrivalForecast
    
    # Get all rooms ordered by floor and room number
    rooms = Room.query.order_by(Room.floor, Room.room_number).all()
    
    # Calculate current statistics
    total_rooms = len(rooms)
    occupied_rooms = sum(1 for r in rooms if r.is_occupied)
    total_patients = sum(r.patient_count for r in rooms)
    total_relatives = sum(r.relative_count for r in rooms)
    total_people = total_patients + total_relatives
    rooms_need_cleaning = sum(1 for r in rooms if r.needs_cleaning)
    
    # Calculate tomorrow's forecast
    checking_out_rooms = [r for r in rooms if r.checking_out_tomorrow]
    leaving_tomorrow = sum(r.total_occupants for r in checking_out_rooms)
    
    tomorrow_date = date.today() + timedelta(days=1)
    forecast = DailyArrivalForecast.query.filter_by(date=tomorrow_date).first()
    arriving_tomorrow = forecast.expected_arrivals if forecast else 0
    
    tomorrow_total = total_people - leaving_tomorrow + arriving_tomorrow
    
    # Group rooms by floor
    rooms_by_floor = {}
    for room in rooms:
        if room.floor not in rooms_by_floor:
            rooms_by_floor[room.floor] = []
        rooms_by_floor[room.floor].append(room)
    
    return render_template(
        'rooms/index.html',
        rooms_by_floor=rooms_by_floor,
        can_manage_occupancy=current_user.is_patient_admin,
        can_manage_cleaning=current_user.is_cleaning_staff,
        # Current statistics
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        total_patients=total_patients,
        total_relatives=total_relatives,
        total_people=total_people,
        rooms_need_cleaning=rooms_need_cleaning,
        # Tomorrow forecast
        leaving_tomorrow=leaving_tomorrow,
        arriving_tomorrow=arriving_tomorrow,
        tomorrow_total=tomorrow_total,
        tomorrow_date=tomorrow_date
    )


@bp.route("/update/<int:room_id>", methods=["POST"])
@login_required
def update_room(room_id):
    """Update room status (occupancy or cleaning)"""
    room = Room.query.get_or_404(room_id)
    
    data = request.get_json()
    action = data.get('action')
    
    # Handle occupancy changes (patient admins only)
    if action in ['set_occupancy']:
        if not current_user.is_patient_admin:
            return jsonify({'error': 'Ingen tilladelse'}), 403
        
        patient_count = int(data.get('patient_count', 0))
        relative_count = int(data.get('relative_count', 0))
        
        # Validate counts
        if patient_count < 0 or patient_count > 2:
            return jsonify({'error': 'Ugyldig antal patienter'}), 400
        if relative_count < 0 or relative_count > 1:
            return jsonify({'error': 'Ugyldig antal pårørende'}), 400
        
        room.patient_count = patient_count
        room.relative_count = relative_count
        room.last_occupancy_change = datetime.utcnow()
        
        # If checking out (setting to 0), mark as needs cleaning
        if patient_count == 0 and relative_count == 0 and room.cleaning_status == CleaningStatus.CLEAN:
            room.cleaning_status = CleaningStatus.NEEDS_CLEANING
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'room': {
                'id': room.id,
                'room_number': room.room_number,
                'patient_count': room.patient_count,
                'relative_count': room.relative_count,
                'total_occupants': room.total_occupants,
                'is_occupied': room.is_occupied,
                'cleaning_status': room.cleaning_status.value,
                'needs_cleaning': room.needs_cleaning
            }
        })
    
    # Handle cleaning status changes (cleaning staff only)
    elif action == 'mark_cleaned':
        if not current_user.is_cleaning_staff:
            return jsonify({'error': 'Ingen tilladelse'}), 403
        
        # Create cleaning log entry
        log = CleaningLog(
            room_id=room.id,
            cleaned_by_id=current_user.id,
            status_before=room.cleaning_status,
            status_after=CleaningStatus.CLEAN
        )
        db.session.add(log)
        
        # Update room status
        room.cleaning_status = CleaningStatus.CLEAN
        room.last_cleaned_at = datetime.utcnow()
        room.last_cleaned_by_id = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'room': {
                'id': room.id,
                'room_number': room.room_number,
                'cleaning_status': room.cleaning_status.value,
                'needs_cleaning': room.needs_cleaning,
                'last_cleaned_at': room.last_cleaned_at.strftime('%Y-%m-%d %H:%M') if room.last_cleaned_at else None
            }
        })
    
    elif action == 'mark_needs_cleaning':
        if not current_user.is_patient_admin:
            return jsonify({'error': 'Ingen tilladelse'}), 403
        
        # Create cleaning log entry
        log = CleaningLog(
            room_id=room.id,
            cleaned_by_id=current_user.id,
            status_before=room.cleaning_status,
            status_after=CleaningStatus.NEEDS_CLEANING
        )
        db.session.add(log)
        
        room.cleaning_status = CleaningStatus.NEEDS_CLEANING
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'room': {
                'id': room.id,
                'room_number': room.room_number,
                'cleaning_status': room.cleaning_status.value,
                'needs_cleaning': room.needs_cleaning
            }
        })
    
    elif action == 'toggle_checkout_tomorrow':
        if not current_user.is_patient_admin:
            return jsonify({'error': 'Ingen tilladelse'}), 403
        
        checkout_tomorrow = data.get('checkout_tomorrow', False)
        room.checking_out_tomorrow = checkout_tomorrow
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'checking_out_tomorrow': room.checking_out_tomorrow
        })
    
    else:
        return jsonify({'error': 'Ugyldig handling'}), 400


@bp.route("/forecast/update", methods=["POST"])
@login_required
def update_forecast():
    """Update daily arrival forecast"""
    if not current_user.is_patient_admin:
        return jsonify({'error': 'Ingen tilladelse'}), 403
    
    from datetime import timedelta
    from dgp_intra.models import DailyArrivalForecast
    
    data = request.get_json()
    expected_arrivals = int(data.get('expected_arrivals', 0))
    
    if expected_arrivals < 0:
        return jsonify({'error': 'Antal ankomster kan ikke være negativt'}), 400
    
    tomorrow_date = date.today() + timedelta(days=1)
    
    # Find or create forecast
    forecast = DailyArrivalForecast.query.filter_by(date=tomorrow_date).first()
    
    if forecast:
        forecast.expected_arrivals = expected_arrivals
        forecast.updated_by_id = current_user.id
        forecast.updated_at = datetime.utcnow()
    else:
        forecast = DailyArrivalForecast(
            date=tomorrow_date,
            expected_arrivals=expected_arrivals,
            updated_by_id=current_user.id
        )
        db.session.add(forecast)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'expected_arrivals': expected_arrivals
    })


@bp.route("/cleaning-logs")
@login_required
def cleaning_logs():
    """View cleaning history (for cleaning staff and admins)"""
    if not (current_user.is_cleaning_staff or current_user.is_patient_admin):
        abort(403)
    
    # Get recent cleaning logs
    logs = (
        CleaningLog.query
        .order_by(CleaningLog.cleaned_at.desc())
        .limit(100)
        .all()
    )
    
    return render_template('rooms/cleaning_logs.html', logs=logs)


@bp.route("/meal-planning")
@login_required
def meal_planning():
    """Show occupied rooms for kitchen meal planning"""
    if not current_user.is_kitchen_staff:
        abort(403)
    
    # Get all occupied rooms
    occupied_rooms = Room.query.filter(
        (Room.patient_count > 0) | (Room.relative_count > 0)
    ).order_by(Room.floor, Room.room_number).all()
    
    # Calculate totals
    total_patients = sum(r.patient_count for r in occupied_rooms)
    total_relatives = sum(r.relative_count for r in occupied_rooms)
    total_people = total_patients + total_relatives
    
    # Group by floor
    rooms_by_floor = {}
    for room in occupied_rooms:
        if room.floor not in rooms_by_floor:
            rooms_by_floor[room.floor] = []
        rooms_by_floor[room.floor].append(room)
    
    return render_template(
        'rooms/meal_planning.html',
        rooms_by_floor=rooms_by_floor,
        total_patients=total_patients,
        total_relatives=total_relatives,
        total_people=total_people
    )


# ============================================================================
# MEAL REGISTRATION ROUTES
# ============================================================================

@bp.route("/meals/<meal_type>")
@login_required
def meal_registration(meal_type):
    """Meal registration view for kitchen staff"""
    if not current_user.is_kitchen_staff:
        abort(403)
    
    # Validate meal type
    if meal_type not in ['breakfast', 'lunch', 'dinner']:
        abort(404)
    
    meal_enum = MealType[meal_type.upper()]
    today = date.today()
    
    # Get all rooms with occupants
    occupied_rooms = Room.query.filter(
        (Room.patient_count > 0) | (Room.relative_count > 0)
    ).order_by(Room.floor, Room.room_number).all()
    
    # Get today's registrations for this meal
    registrations = MealRegistration.query.filter_by(
        meal_type=meal_enum,
        date=today
    ).all()
    
    # Create a lookup dict for quick access
    registered_rooms = {reg.room_id: reg for reg in registrations}
    
    # Group rooms by floor
    rooms_by_floor = {}
    for room in occupied_rooms:
        if room.floor not in rooms_by_floor:
            rooms_by_floor[room.floor] = []
        
        # Add registration status to room
        room.registration = registered_rooms.get(room.id)
        rooms_by_floor[room.floor].append(room)
    
    # Calculate totals
    total_registered = sum(reg.people_count for reg in registrations)
    total_billable = sum(reg.billable_count for reg in registrations)
    
    # Meal display names
    meal_names = {
        'breakfast': 'Morgenmad',
        'lunch': 'Frokost',
        'dinner': 'Aftensmad'
    }
    
    return render_template(
        'rooms/meal_registration.html',
        meal_type=meal_type,
        meal_name=meal_names[meal_type],
        meal_enum=meal_enum,
        rooms_by_floor=rooms_by_floor,
        total_registered=total_registered,
        total_billable=total_billable,
        today=today
    )


@bp.route("/meals/register/<int:room_id>", methods=["POST"])
@login_required
def register_meal(room_id):
    """Register a meal for a room"""
    if not current_user.is_kitchen_staff:
        return jsonify({'error': 'Ingen tilladelse'}), 403
    
    room = Room.query.get_or_404(room_id)
    data = request.get_json()
    
    meal_type = data.get('meal_type')
    people_count = int(data.get('people_count', 0))
    patients_count = int(data.get('patients_count', 0))
    relatives_count = int(data.get('relatives_count', 0))
    
    # Validate
    if meal_type not in ['breakfast', 'lunch', 'dinner']:
        return jsonify({'error': 'Ugyldig måltidstype'}), 400
    
    if people_count < 1:
        return jsonify({'error': 'Mindst 1 person skal spise'}), 400
    
    if people_count != (patients_count + relatives_count):
        return jsonify({'error': 'Antal personer matcher ikke'}), 400
    
    meal_enum = MealType[meal_type.upper()]
    today = date.today()
    
    # Check if already registered
    existing = MealRegistration.query.filter_by(
        room_id=room_id,
        meal_type=meal_enum,
        date=today
    ).first()
    
    if existing:
        # Update existing registration
        existing.people_count = people_count
        existing.patients_count = patients_count
        existing.relatives_count = relatives_count
        existing.registered_by_id = current_user.id
        existing.registered_at = datetime.utcnow()
    else:
        # Create new registration
        registration = MealRegistration(
            room_id=room_id,
            meal_type=meal_enum,
            date=today,
            people_count=people_count,
            patients_count=patients_count,
            relatives_count=relatives_count,
            registered_by_id=current_user.id
        )
        db.session.add(registration)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'room_number': room.room_number,
        'people_count': people_count
    })


@bp.route("/meals/unregister/<int:room_id>", methods=["POST"])
@login_required
def unregister_meal(room_id):
    """Unregister a meal for a room"""
    if not current_user.is_kitchen_staff:
        return jsonify({'error': 'Ingen tilladelse'}), 403
    
    data = request.get_json()
    meal_type = data.get('meal_type')
    
    if meal_type not in ['breakfast', 'lunch', 'dinner']:
        return jsonify({'error': 'Ugyldig måltidstype'}), 400
    
    meal_enum = MealType[meal_type.upper()]
    today = date.today()
    
    # Find and delete registration
    registration = MealRegistration.query.filter_by(
        room_id=room_id,
        meal_type=meal_enum,
        date=today
    ).first()
    
    if registration:
        db.session.delete(registration)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Ingen registrering fundet'}), 404


@bp.route("/meals/summary")
@login_required
def meal_summary():
    """Daily meal summary for kitchen staff"""
    if not current_user.is_kitchen_staff:
        abort(403)
    
    from datetime import timedelta
    from dgp_intra.models import DailyArrivalForecast
    
    today = date.today()
    
    # Get all registrations for today
    registrations = MealRegistration.query.filter_by(date=today).all()
    
    # Group by meal type
    by_meal = {
        'breakfast': [],
        'lunch': [],
        'dinner': []
    }
    
    totals = {
        'breakfast': {'count': 0, 'billable': 0},
        'lunch': {'count': 0, 'billable': 0},
        'dinner': {'count': 0, 'billable': 0}
    }
    
    for reg in registrations:
        meal_key = reg.meal_type.value
        by_meal[meal_key].append(reg)
        totals[meal_key]['count'] += reg.people_count
        totals[meal_key]['billable'] += reg.billable_count
    
    # Calculate current and tomorrow forecast
    rooms = Room.query.all()
    current_occupancy = sum(r.total_occupants for r in rooms)
    
    checking_out_rooms = [r for r in rooms if r.checking_out_tomorrow]
    leaving_tomorrow = sum(r.total_occupants for r in checking_out_rooms)
    
    tomorrow_date = today + timedelta(days=1)
    forecast = DailyArrivalForecast.query.filter_by(date=tomorrow_date).first()
    arriving_tomorrow = forecast.expected_arrivals if forecast else 0
    
    tomorrow_forecast = current_occupancy - leaving_tomorrow + arriving_tomorrow
    
    return render_template(
        'rooms/meal_summary.html',
        by_meal=by_meal,
        totals=totals,
        today=today,
        current_occupancy=current_occupancy,
        tomorrow_forecast=tomorrow_forecast,
        leaving_tomorrow=leaving_tomorrow,
        arriving_tomorrow=arriving_tomorrow
    )

# ============================================================================
# KITCHEN DASHBOARD
# ============================================================================

@bp.route("/kitchen")
@login_required
def kitchen_dashboard():
    """Kitchen staff dashboard with registrations and payments"""
    if not current_user.is_kitchen_staff:
        abort(403)
    
    from datetime import timedelta
    from dgp_intra.models import User, LunchRegistration, BreakfastRegistration, DailyArrivalForecast
    from sqlalchemy import func
    
    today = date.today()
    
    # Current and tomorrow occupancy
    rooms = Room.query.all()
    current_occupancy = sum(r.total_occupants for r in rooms)
    
    checking_out_rooms = [r for r in rooms if r.checking_out_tomorrow]
    leaving_tomorrow = sum(r.total_occupants for r in checking_out_rooms)
    
    tomorrow_date = today + timedelta(days=1)
    forecast = DailyArrivalForecast.query.filter_by(date=tomorrow_date).first()
    arriving_tomorrow = forecast.expected_arrivals if forecast else 0
    
    tomorrow_forecast = current_occupancy - leaving_tomorrow + arriving_tomorrow
    
    # Get this week's lunch registrations (staff)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    registrations = (
        LunchRegistration.query
        .filter(LunchRegistration.date >= week_start)
        .filter(LunchRegistration.date <= week_end)
        .filter(LunchRegistration.date >= today)  # Only today and future
        .order_by(LunchRegistration.date)
        .all()
    )
    
    # Group by date
    grouped_registrations = {}
    for reg in registrations:
        if reg.date not in grouped_registrations:
            grouped_registrations[reg.date] = []
        grouped_registrations[reg.date].append(reg.user)
    
    # Get Friday breakfast registrations
    # Find next Friday
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.weekday() != 4:
        days_until_friday = 7
    friday = today + timedelta(days=days_until_friday)
    
    # Get breakfast registrations using BreakfastRegistration table
    breakfast_registrations = (
        BreakfastRegistration.query
        .filter(BreakfastRegistration.date == friday)
        .all()
    )
    breakfast_users = [reg.user for reg in breakfast_registrations]
    
    # Get users who owe money
    users_who_owe = (
        User.query
        .filter(User.owes > 0)
        .order_by(User.owes.desc())
        .all()
    )
    
    return render_template(
        'rooms/kitchen_dashboard.html',
        current_occupancy=current_occupancy,
        tomorrow_forecast=tomorrow_forecast,
        leaving_tomorrow=leaving_tomorrow,
        arriving_tomorrow=arriving_tomorrow,
        grouped_registrations=grouped_registrations,
        breakfast_users=breakfast_users,
        breakfast_count=len(breakfast_users),
        breakfast_date=friday,
        users_who_owe=users_who_owe,
        today=today
    )