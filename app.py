from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, not_
import os
from datetime import datetime
from sqlalchemy.sql import func
import random
import secrets
import string
import smtplib
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'supersecretpasskey123lol#'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.securebytechronicles.tech'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''  # Update with your Gmail email address
app.config['MAIL_PASSWORD'] = ''     # Update with your Gmail password

mail = Mail(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, default=100.0)
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

@app.context_processor
def utility_functions():
    def abs_filter(value):
        return abs(value)
    return dict(abs=abs_filter)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/terms_of_use')
def terms_of_use():
    return render_template('terms_of_use.html')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if request.method == 'POST':
            new_username = request.form['username']
            new_email = request.form['email']
            new_password = request.form['password']

            existing_user_with_username = User.query.filter_by(username=new_username).first()
            existing_user_with_email = User.query.filter_by(email=new_email).first()

            if existing_user_with_username and existing_user_with_username.id != user.id:
                flash('Username already in use. Please choose a different one.', 'error')
            elif existing_user_with_email and existing_user_with_email.id != user.id:
                flash('Email already in use. Please choose a different one.', 'error')
            else:
                user.username = new_username
                user.email = new_email
                if new_password:  # Check if password is provided
                    user.password = new_password  # Update the password
                db.session.commit()
                flash('Settings updated successfully!', 'success')
                return redirect(url_for('settings'))

        return render_template('settings.html', user=user, update_password=True)
    else:
        flash('Please login to access the settings', 'error')
        return redirect(url_for('login'))



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        try:
            max_user_id = db.session.query(func.max(User.id)).scalar()
            next_user_id = 1 if max_user_id is None else max_user_id + 1
            
            user = User(username=username, email=email, password=password, id=9453000000 + next_user_id)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists', 'error')  
            return redirect(url_for('register'))
    return render_template('register.html')

# Route for login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

# Route for forgot password page
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # Generate a new password (you can use any method to generate a strong password)
        new_password = generate_strong_password()
        # Update the user's password in the database
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = new_password
            db.session.commit()
            # Send the new password to the user's email
            send_password_reset_email(email, new_password)
            flash('A new password has been sent to your email address', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid email address', 'error')
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

def generate_strong_password():
   
    password_characters = string.ascii_letters + string.digits + string.punctuation
    new_password = ''.join(secrets.choice(password_characters) for i in range(12))
    return new_password

def send_password_reset_email(email, new_password):
    msg = Message('Password Reset', sender='', recipients=[email])# Update with your Gmail email address
    msg.body = f'Your new password is: {new_password}'
    mail.send(msg)

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        amount = float(request.form['amount'])
        if amount <= 0:
            flash('Deposit amount must be positive', 'error')
            return redirect(url_for('dashboard'))
        
        user.balance += amount
        transaction = Transaction(user_id=user.id, amount=amount, description=f'Deposit by {user.username}')
        db.session.add(transaction)
        db.session.commit()
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        recent_transactions_sent = user.transactions.filter(Transaction.amount < 0).order_by(Transaction.timestamp.desc()).limit(10).all()
        recent_transactions_received = user.transactions.filter(Transaction.amount > 0).order_by(Transaction.timestamp.desc()).limit(10).all()

        if request.method == 'POST':
            recipient_id = request.form['recipient']
            amount = float(request.form['amount'])
            recipient = User.query.get(recipient_id)
            if recipient:
                if amount <= 0:
                    flash('Transfer amount must be positive', 'error')
                    return redirect(url_for('dashboard'))
                elif user.balance < amount:
                    flash('Insufficient balance', 'error')
                    return redirect(url_for('dashboard'))
                else:
                    user.balance -= amount
                    recipient.balance += amount
                    transaction_sent = Transaction(user_id=user.id, amount=-amount, description=f'Transfer to {recipient.username}')
                    transaction_received = Transaction(user_id=recipient.id, amount=amount, description=f'Received from {user.username}')
                    db.session.add_all([transaction_sent, transaction_received])
                    db.session.commit()
                    flash('Transaction successful', 'success')
                    return redirect(url_for('dashboard'))
            else:
                flash('Recipient account not found', 'error')
                return redirect(url_for('dashboard'))
        return render_template('dashboard.html', user=user, transactions_sent=recent_transactions_sent, transactions_received=recent_transactions_received)
    else:
        flash('Please login to access the dashboard', 'error')
        return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/submit_contact_form', methods=['POST'])
def submit_contact_form():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        contact = Contact(name=name, email=email, message=message)
        db.session.add(contact)
        db.session.commit()

        flash('Your message has been processed!', 'success')

        return redirect(url_for('contact'))

if __name__ == '__main__':
    app.run(debug=True)

