from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import functools
import string
import secrets
import traceback
from datetime import datetime

app = Flask(__name__, template_folder='Template/requirement')
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkeyforbridgethings")

# Resolve absolute path to .env relative to this script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ENV_PATH)
except ImportError:
    # Custom fallback loader if python-dotenv is not installed
    def load_env_variables():
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            key, val = parts[0].strip(), parts[1].strip()
                            os.environ[key] = val.strip("\"'")
    load_env_variables()

def _get_smtp_connection():
    """Internal helper to create and return an authenticated SMTP connection."""
    server_name = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    try:
        port = int(os.environ.get("SMTP_PORT", 587))
    except ValueError:
        port = 587
    username = os.environ.get("SMTP_USERNAME", "your_email@gmail.com")
    password = os.environ.get("SMTP_PASSWORD", "your_app_password")

    if username == "your_email@gmail.com" or password == "your_app_password":
        print("CRITICAL: SMTP credentials are placeholders. Please configure the .env file.")
        return None, None

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(server_name, port, timeout=10)
        else:
            server = smtplib.SMTP(server_name, port, timeout=10)
            server.starttls()
        server.login(username, password)
        return server, username
    except Exception as e:
        print(f"SMTP connection/login failed: {e}")
        return None, None

def send_email_notification(assigned_engineer, ticket):
    """Sends a notification email to the assigned support engineer and main admins."""
    server_name = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    try:
        port = int(os.environ.get("SMTP_PORT", 587))
    except ValueError:
        port = 587
    username = os.environ.get("SMTP_USERNAME", "your_email@gmail.com")
    password = os.environ.get("SMTP_PASSWORD", "your_app_password")
    sender = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
    
    # Fetch notification emails from database, fallback to env variable if none configured
    main_emails = [e.email.strip() for e in DefaultEmail.query.all()]
    if not main_emails:
        main_emails_str = os.environ.get("MAIN_EMAILS", "admin@example.com")
        main_emails = [email.strip() for email in main_emails_str.split(",") if email.strip()]

    # Build list of unique recipients (assigned engineer + main emails)
    recipients = []
    if assigned_engineer and "@" in assigned_engineer:
        recipients.append(assigned_engineer.strip())
    for email in main_emails:
        if "@" in email and email not in recipients:
            recipients.append(email.strip())

    if not recipients:
        print("No recipients configured for email notification.")
        return False

    server, _ = _get_smtp_connection()
    if not server:
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"New Ticket Assigned: ID {ticket.id} ({ticket.priority} Priority)"

        body = f"Dear Support Team,\n\nA new ticket has been created and assigned.\n\n" \
               f"Details:\n- ID: {ticket.id}\n- Engineer: {assigned_engineer}\n" \
               f"- Priority: {ticket.priority}\n\nDescription:\n{ticket.description}"
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with server:
            server.sendmail(sender, recipients, msg.as_string())
        print(f"Notification email successfully sent to recipients: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"Failed to send email to recipients: {', '.join(recipients)}. Error: {e}")
        traceback.print_exc()
        return False

def send_customer_receipt_email(ticket):
    """Sends a receipt confirmation email to the customer."""
    sender = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
    customer_email = ticket.customer_email.strip() if ticket.customer_email else ""
    if not customer_email or "@" not in customer_email:
        print("No valid customer email configured for notification.")
        return False

    server, _ = _get_smtp_connection()
    if not server:
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = customer_email
        msg['Subject'] = f"BridgeThings Support - Ticket #{ticket.id} Created Successfully"

        body = f"Dear {ticket.customer_name},\n\nWe have received your support request.\n" \
               f"Ticket ID: #{ticket.id}\n\nDescription:\n{ticket.description}"
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with server:
            server.sendmail(sender, [customer_email], msg.as_string())
        print(f"Receipt confirmation email successfully sent to customer: {customer_email}")
        return True
    except Exception as e:
        print(f"Failed to send customer email confirmation to {customer_email}. Error: {e}")
        traceback.print_exc()
        return False

def send_password_reset_email(user_email, temporary_password):
    """Sends a temporary password email to the user."""
    sender = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
    server, _ = _get_smtp_connection()
    if not server:
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = user_email
        msg['Subject'] = "BridgeThings Ticket Portal - Temporary Password Reset"

        body = f"""
Dear User,

A password reset was requested for your account on the BridgeThings Ticket Portal.

Your temporary password is: {temporary_password}

Please sign in with this temporary password and change it.

Best regards,
BridgeThings Support Team
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with server:
            server.sendmail(sender, [user_email], msg.as_string())
        print(f"Temporary password successfully sent to {user_email}")
        return True
    except Exception as e:
        print(f"Failed to send temporary password email to {user_email}. Error: {e}")
        traceback.print_exc()
        return False

def send_ticket_update_notification(ticket, old_status, old_engineer):
    """Sends a notification email when a ticket is updated (status or engineer change)."""
    sender = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
    server, _ = _get_smtp_connection()
    if not server:
        return False

    # Fetch notification emails from database, fallback to env variable if none configured
    main_emails = [e.email.strip() for e in DefaultEmail.query.all()]
    if not main_emails:
        main_emails_str = os.environ.get("MAIN_EMAILS", "admin@example.com")
        main_emails = [email.strip() for email in main_emails_str.split(",") if email.strip()]

    # Build list of unique recipients (assigned engineer + old engineer + main emails)
    recipients = []
    if ticket.support_engineer and "@" in ticket.support_engineer:
        recipients.append(ticket.support_engineer.strip())
    if old_engineer and "@" in old_engineer and old_engineer.strip() not in recipients:
        recipients.append(old_engineer.strip())
    for email in main_emails:
        if "@" in email and email not in recipients:
            recipients.append(email.strip())

    if not recipients:
        print("No recipients configured for update email notification.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"BridgeThings Support - Ticket #{ticket.id} Updated"

        body = f"""Dear Support Team,

Ticket #{ticket.id} has been updated.

Change Details:
- Assigned Engineer: {old_engineer if old_engineer else 'Unassigned'} -> {ticket.support_engineer if ticket.support_engineer else 'Unassigned'}
- Status: {old_status} -> {ticket.status}
- Priority: {ticket.priority}

Ticket Info:
- Customer Name: {ticket.customer_name}
- Customer Email: {ticket.customer_email}
- MAC ID: {ticket.mac_id}
- Deadline: {ticket.deadline if ticket.deadline else 'Not set'}

Description:
{ticket.description}

Please log in to the dashboard to review the changes.

Best regards,
BridgeThings Ticket System
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with server:
            server.sendmail(sender, recipients, msg.as_string())
        print(f"Update notification email successfully sent to recipients: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"Failed to send update email to recipients: {', '.join(recipients)}. Error: {e}")
        traceback.print_exc()
        return False

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload Folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Database
db = SQLAlchemy(app)

# Create Upload Folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Database Tables
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(100))
    mac_id = db.Column(db.String(100))
    description = db.Column(db.Text)
    priority = db.Column(db.String(20))
    status = db.Column(db.String(20))
    support_engineer = db.Column(db.String(100))
    sold_date = db.Column(db.String(20))
    deadline = db.Column(db.String(20), nullable=True)
    image = db.Column(db.String(200))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class SupportEngineer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)


class DefaultEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)


# Create Database and Seed Default Admin User
with app.app_context():
    db.create_all()
    # Check if 'deadline' column exists in 'ticket' table
    try:
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('ticket')]
        if 'deadline' not in columns:
            print("Adding missing 'deadline' column to the 'ticket' table...")
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE ticket ADD COLUMN deadline VARCHAR(20)"))
                conn.commit()
            print("Column added successfully.")
    except Exception as e:
        print(f"Error checking/migrating database schema: {e}")

    # Check if any users exist, if not seed default user
    if User.query.first() is None:
        admin_user = User(
            username='admin',
            email='admin@example.com'
        )
        admin_user.set_password('Admin@123')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created successfully (username: admin, password: Admin@123)")

    # Seed default Support Engineers if empty
    if SupportEngineer.query.first() is None:
        default_engineers = [
            SupportEngineer(name="Engineer 1", email="engineer1@example.com"),
            SupportEngineer(name="Engineer 2", email="engineer2@example.com"),
            SupportEngineer(name="Engineer 3", email="engineer3@example.com")
        ]
        for eng in default_engineers:
            db.session.add(eng)
        db.session.commit()
        print("Default support engineers seeded successfully.")

    # Seed default notification CC email if empty
    if DefaultEmail.query.first() is None:
        default_notification = DefaultEmail(email="admin@example.com")
        db.session.add(default_notification)
        db.session.commit()
        print("Default notification email seeded successfully.")


# Authentication Decorator
def login_required(redirect_endpoint='login'):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for(redirect_endpoint))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Home Page
@app.route('/')
@login_required(redirect_endpoint='login')
def home():
    tickets = Ticket.query.all()
    
    # Calculate stats
    total_tickets = len(tickets)
    open_tickets = sum(1 for t in tickets if t.status == 'Open')
    in_progress_tickets = sum(1 for t in tickets if t.status == 'In Progress')
    resolved_tickets = sum(1 for t in tickets if t.status == 'Resolved')
    
    # Overdue calculation: if deadline is set, status is not Resolved, and deadline date < current date
    today_str = datetime.today().strftime('%Y-%m-%d')
    overdue_tickets = 0
    for t in tickets:
        if t.status != 'Resolved' and t.deadline:
            if t.deadline < today_str:
                overdue_tickets += 1
                t.is_overdue = True
            else:
                t.is_overdue = False
        else:
            t.is_overdue = False

    engineers = SupportEngineer.query.all()
    default_emails = DefaultEmail.query.all()
    portal_users = User.query.all()
    engineer_map = {eng.email: eng.name for eng in engineers}
    return render_template(
        'dashboard.html',
        tickets=tickets,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_tickets=resolved_tickets,
        overdue_tickets=overdue_tickets,
        today_str=today_str,
        engineers=engineers,
        default_emails=default_emails,
        portal_users=portal_users,
        engineer_map=engineer_map
    )


# Customer Admin Monitoring Page
@app.route('/customers')
@login_required(redirect_endpoint='login')
def customers():
    # Fetch unique customers and their ticket counts for monitoring
    customer_data = db.session.query(
        Ticket.customer_name, 
        Ticket.customer_email, 
        db.func.count(Ticket.id).label('ticket_count')
    ).group_by(Ticket.customer_email).all()
    return render_template('customers.html', customers=customer_data)


# Support Engineer Monitoring Portal
@app.route('/engineer_portal')
@login_required(redirect_endpoint='engineer_login')
def engineer_portal():
    tickets = Ticket.query.all()
    
    # Calculate simple stats for monitoring
    total_tickets = len(tickets)
    open_tickets = sum(1 for t in tickets if t.status == 'Open')
    in_progress_tickets = sum(1 for t in tickets if t.status == 'In Progress')
    resolved_tickets = sum(1 for t in tickets if t.status == 'Resolved')
    
    today_str = datetime.today().strftime('%Y-%m-%d')
    for t in tickets:
        if t.status != 'Resolved' and t.deadline:
            t.is_overdue = t.deadline < today_str
        else:
            t.is_overdue = False

    return render_template('engineer_portal.html', 
                         tickets=tickets,
                         total_tickets=total_tickets,
                         open_tickets=open_tickets,
                         in_progress_tickets=in_progress_tickets,
                         resolved_tickets=resolved_tickets,
                         today_str=today_str)


# Engineer Login Page
@app.route('/engineer_login', methods=['GET', 'POST'])
def engineer_login():
    if 'user_id' in session:
        return redirect(url_for('engineer_portal'))

    if request.method == 'POST':
        username_or_email = request.form['username'].strip()
        password = request.form['password']

        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            flash('Logged in successfully to Engineer Portal.', 'success')
            return redirect(url_for('engineer_portal'))
        else:
            flash('Invalid username/email or password.', 'error')

    return render_template('engineer_login.html')


# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username_or_email = request.form['username'].strip()
        password = request.form['password']

        # Look up by either username or email
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username/email or password.', 'error')

    return render_template('login.html')


# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        # Check if username or email already exists
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash('Username is already taken.', 'error')
            return render_template('register.html')

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email is already registered.', 'error')
            return render_template('register.html')

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# Forgot Password Page
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()

        user = User.query.filter_by(email=email).first()

        if user:
            # Generate a secure temporary password
            chars = string.ascii_letters + string.digits
            temp_password = ''.join(secrets.choice(chars) for _ in range(10))

            # Update password
            user.set_password(temp_password)
            db.session.commit()

            # Send email
            email_sent = send_password_reset_email(user.email, temp_password)

            if email_sent:
                flash('A temporary password has been sent to your email address.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Error sending password reset email. Please contact the administrator.', 'error')
        else:
            flash('No account found with that email address.', 'error')

    return render_template('forgot_password.html')


# Change Password Page
@app.route('/change_password', methods=['GET', 'POST'])
@login_required(redirect_endpoint='login')
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_email = request.form.get('email', '').strip()
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        user = db.session.get(User, session['user_id'])

        if not user or not user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password.html', user_email=session.get('email'))

        # Update Email if changed
        if new_email and new_email != user.email:
            existing = User.query.filter(User.email == new_email, User.id != user.id).first()
            if existing:
                flash('This email address is already in use by another account.', 'error')
                return render_template('change_password.html', user_email=user.email)
            user.email = new_email
            session['email'] = new_email

        # Update Password if provided
        if new_password:
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return render_template('change_password.html', user_email=user.email)
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'error')
                return render_template('change_password.html', user_email=user.email)
            user.set_password(new_password)

        db.session.commit()
        flash('Account settings updated successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('change_password.html', user_email=session.get('email'))


# Create Ticket
@app.route('/create_ticket', methods=['POST'])
@login_required(redirect_endpoint='login')
def create_ticket():
    customer_name = request.form['customer_name']
    customer_email = request.form['customer_email']
    mac_id = request.form['mac_id']
    description = request.form['description']
    priority = request.form['priority']
    status = request.form['status']
    support_engineer = request.form['support_engineer']
    sold_date = request.form['sold_date']
    deadline = request.form.get('deadline')

    # Image Upload
    image = request.files.get('mobile_image')
    image_filename = ""
    if image and image.filename != "":
        original_filename = secure_filename(image.filename)
        # Make the filename unique to prevent overwrites
        import uuid
        name, ext = os.path.splitext(original_filename)
        image_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        image.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                image_filename
            )
        )

    # Save Ticket
    new_ticket = Ticket(
        customer_name=customer_name,
        customer_email=customer_email,
        mac_id=mac_id,
        description=description,
        priority=priority,
        status=status,
        support_engineer=support_engineer,
        sold_date=sold_date,
        deadline=deadline,
        image=image_filename
    )

    db.session.add(new_ticket)
    db.session.commit()

    # Send email notification to the assigned support engineer and the three main emails
    engineer_email_sent = send_email_notification(support_engineer, new_ticket)
    # Send receipt confirmation to the customer
    customer_email_sent = send_customer_receipt_email(new_ticket)

    # Check if SMTP configuration is set to placeholders
    smtp_user = os.environ.get("SMTP_USERNAME", "your_email@gmail.com")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "your_app_password")
    is_placeholder = (smtp_user == "your_email@gmail.com" or smtp_pass == "your_app_password" or not smtp_user or not smtp_pass)

    if is_placeholder:
        flash('Ticket created successfully! (Email notifications were skipped because SMTP is not configured.)', 'info')
    elif engineer_email_sent and customer_email_sent:
        flash('Ticket created and notification emails sent successfully to both customer and engineer!', 'success')
    elif engineer_email_sent:
        flash('Ticket created. Support engineer notified, but customer email failed to send.', 'warning')
    elif customer_email_sent:
        flash('Ticket created. Customer notified, but support engineer email failed to send.', 'warning')
    else:
        flash('Ticket created, but there was an error sending the notification emails. Check server logs.', 'warning')

    print(f"Ticket {new_ticket.id} saved successfully.")
    return redirect(url_for('home'))


# Delete Ticket
@app.route('/delete_ticket/<int:id>')
@login_required(redirect_endpoint='login')
def delete_ticket(id):
    ticket = db.session.get(Ticket, id)
    if ticket:
        if ticket.image:
            try:
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], ticket.image)
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception as e:
                print(f"Error removing ticket image from disk: {e}")
        db.session.delete(ticket)
        db.session.commit()
        flash(f'Ticket #{id} deleted successfully.', 'success')
    else:
        flash('Ticket not found.', 'error')
    return redirect(url_for('home'))


# Add Support Engineer
@app.route('/add_engineer', methods=['POST'])
@login_required(redirect_endpoint='login')
def add_engineer():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    if not name or not email:
        flash('Engineer name and email are required.', 'error')
        return redirect(url_for('home'))
    
    # Check if email already exists
    existing = SupportEngineer.query.filter_by(email=email).first()
    if existing:
        flash('An engineer with this email already exists.', 'error')
        return redirect(url_for('home'))
        
    new_engineer = SupportEngineer(name=name, email=email)
    db.session.add(new_engineer)
    db.session.commit()
    flash(f'Support engineer {name} added successfully!', 'success')
    return redirect(url_for('home'))


# Delete Support Engineer
@app.route('/delete_engineer/<int:id>')
@login_required(redirect_endpoint='login')
def delete_engineer(id):
    engineer = db.session.get(SupportEngineer, id)
    if engineer:
        db.session.delete(engineer)
        db.session.commit()
        flash('Support engineer removed successfully.', 'success')
    return redirect(url_for('home'))


# Add Default CC Email
@app.route('/add_default_email', methods=['POST'])
@login_required(redirect_endpoint='login')
def add_default_email():
    email = request.form.get('email', '').strip()
    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('home'))
        
    existing = DefaultEmail.query.filter_by(email=email).first()
    if existing:
        flash('This email is already in the default notification list.', 'error')
        return redirect(url_for('home'))
        
    new_email = DefaultEmail(email=email)
    db.session.add(new_email)
    db.session.commit()
    flash(f'Notification email {email} added successfully!', 'success')
    return redirect(url_for('home'))


# Delete Default CC Email
@app.route('/delete_default_email/<int:id>')
@login_required(redirect_endpoint='login')
def delete_default_email(id):
    email = db.session.get(DefaultEmail, id)
    if email:
        db.session.delete(email)
        db.session.commit()
        flash('Notification email removed successfully.', 'success')
    return redirect(url_for('home'))


# Create Portal User
@app.route('/create_portal_user', methods=['POST'])
@login_required(redirect_endpoint='login')
def create_portal_user():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password')

    if not username or not email or not password:
        flash('All fields are required.', 'error')
        return redirect(url_for('home'))

    # Check if username or email already exists
    existing_username = User.query.filter_by(username=username).first()
    if existing_username:
        flash('Username is already taken.', 'error')
        return redirect(url_for('home'))

    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        flash('Email is already registered.', 'error')
        return redirect(url_for('home'))

    # Create new user
    try:
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Portal user account for "{username}" created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating portal user: {str(e)}', 'error')

    return redirect(url_for('home'))


# Delete Portal User
@app.route('/delete_portal_user/<int:id>')
@login_required(redirect_endpoint='login')
def delete_portal_user(id):
    # Prevent self-deletion
    if id == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('home'))

    user = db.session.get(User, id)
    if user:
        try:
            db.session.delete(user)
            db.session.commit()
            flash(f'Portal user account "{user.username}" removed successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting user: {str(e)}', 'error')
    else:
        flash('User not found.', 'error')
    return redirect(url_for('home'))


# Edit Ticket Details
@app.route('/edit_ticket/<int:id>', methods=['POST'])
@login_required(redirect_endpoint='login')
def edit_ticket(id):
    ticket = db.session.get(Ticket, id)
    if not ticket:
        flash('Ticket not found.', 'error')
        return redirect(url_for('home'))

    old_status = ticket.status
    old_engineer = ticket.support_engineer

    # Retrieve values
    ticket.customer_name = request.form['customer_name']
    ticket.customer_email = request.form['customer_email']
    ticket.mac_id = request.form['mac_id']
    ticket.description = request.form['description']
    ticket.priority = request.form['priority']
    ticket.status = request.form['status']
    ticket.support_engineer = request.form['support_engineer']
    ticket.sold_date = request.form['sold_date']
    ticket.deadline = request.form.get('deadline')

    # Handle image upload if a new one is selected
    image = request.files.get('mobile_image')
    if image and image.filename != "":
        # Remove old image from disk
        if ticket.image:
            try:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], ticket.image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            except Exception as e:
                print(f"Error removing old image: {e}")

        original_filename = secure_filename(image.filename)
        import uuid
        name, ext = os.path.splitext(original_filename)
        image_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        ticket.image = image_filename

    db.session.commit()

    # Send notifications if status or engineer changed
    status_changed = (ticket.status != old_status)
    engineer_changed = (ticket.support_engineer != old_engineer)

    if status_changed or engineer_changed:
        smtp_user = os.environ.get("SMTP_USERNAME", "your_email@gmail.com")
        smtp_pass = os.environ.get("SMTP_PASSWORD", "your_app_password")
        is_placeholder = (smtp_user == "your_email@gmail.com" or smtp_pass == "your_app_password" or not smtp_user or not smtp_pass)
        
        if is_placeholder:
            flash('Ticket updated successfully! (Email notifications were skipped because SMTP is not configured.)', 'info')
        else:
            email_sent = send_ticket_update_notification(ticket, old_status, old_engineer)
            if email_sent:
                flash('Ticket updated and notification emails sent successfully!', 'success')
            else:
                flash('Ticket updated, but notification email failed to send. Check server logs.', 'warning')
    else:
        flash('Ticket updated successfully!', 'success')

    return redirect(url_for('home'))


# Update Ticket Status Inline
@app.route('/update_ticket_status/<int:id>', methods=['POST'])
@login_required(redirect_endpoint='login')
def update_ticket_status(id):
    ticket = db.session.get(Ticket, id)
    if not ticket:
        flash('Ticket not found.', 'error')
        return redirect('/')

    old_status = ticket.status
    new_status = request.form.get('status')
    if new_status in ['Open', 'In Progress', 'Resolved'] and new_status != old_status:
        ticket.status = new_status
        db.session.commit()

        # Send notifications
        smtp_user = os.environ.get("SMTP_USERNAME", "your_email@gmail.com")
        smtp_pass = os.environ.get("SMTP_PASSWORD", "your_app_password")
        is_placeholder = (smtp_user == "your_email@gmail.com" or smtp_pass == "your_app_password" or not smtp_user or not smtp_pass)
        
        if is_placeholder:
            flash(f'Ticket #{id} status updated to {new_status}! (Email notifications skipped - SMTP not configured).', 'info')
        else:
            email_sent = send_ticket_update_notification(ticket, old_status, ticket.support_engineer)
            if email_sent:
                flash(f'Ticket #{id} status updated to {new_status} and notification emails sent!', 'success')
            else:
                flash(f'Ticket #{id} status updated to {new_status}, but notification email failed to send.', 'warning')
    else:
        flash('No status change detected or invalid status.', 'info')

    return redirect(request.referrer or '/')


# Run Server
if __name__ == '__main__':
    app.run(debug=True)