from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from datetime import datetime
import sqlite3
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite database setup
DATABASE = 'finance_tracker.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            payment_method TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'username' in session:
        user_id = session['user_id']
        username = session['username']
        
        # Fetch transactions from the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM transactions WHERE user_id = ?", (user_id,))
        transactions = c.fetchall()
        
        # Compute the sum of transaction amounts for each payment method
        total_amount = sum(transaction[2] for transaction in transactions)
        total_upi = sum(transaction[2] for transaction in transactions if transaction[6] == 'UPI')
        total_cash = sum(transaction[2] for transaction in transactions if transaction[6] == 'Cash')
        
        conn.close()

        return render_template('index.html', username=username, total_amount=total_amount, total_upi=total_upi, total_cash=total_cash)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]  # Store user_id in session
            session['username'] = user[1]  # Store username in session
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = c.fetchone()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
        else:
            c.execute("INSERT INTO users (username, email, phone, password) VALUES (?, ?, ?, ?)",
                      (username, email, phone, password))
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/transactions')
def transactions():
    if 'username' in session:
        user_id = session['user_id']  # Assuming you store user_id in session
        username = session['username']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM transactions WHERE user_id = ?", (user_id,))
        transactions = c.fetchall()
        conn.close()

        return render_template('transaction.html', transactions=transactions, username=username)
    else:
        return redirect(url_for('login'))



@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'username' in session:
        user_id = session['user_id']
        date = request.form['date']
        category = request.form['category']
        amount = request.form['amount']
        payment_method = request.form['payment_method']
        trans_type = request.form['type']  # <-- New field here
        description = request.form['notes']

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO transactions (user_id, date, category, amount, payment_method, type, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, category, amount, payment_method, trans_type, description))
        conn.commit()
        conn.close()

        return redirect(url_for('transactions'))
    else:
        return redirect(url_for('login'))
    
@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    if 'username' in session:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        conn.close()
        flash('Transaction deleted successfully.', 'success')
    else:
        flash('You must be logged in to delete a transaction.', 'error')
    return redirect(url_for('transactions'))

@app.route('/daily_spending_data')
def daily_spending_data():
    if 'username' in session:
        user_id = session['user_id']
        
        # Fetch daily spending data from the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT date, SUM(amount) FROM transactions WHERE user_id = ? GROUP BY date", (user_id,))
        data = c.fetchall()
        conn.close()

        # Format data for Chart.js
        labels = [row[0] for row in data]
        amounts = [row[1] for row in data]

        return jsonify({'labels': labels, 'amounts': amounts})
    else:
        return redirect(url_for('login'))

@app.route('/monthly_spending_data')
def monthly_spending_data():
    if 'username' in session:
        user_id = session['user_id']
        
        # Fetch monthly spending data from the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT strftime('%Y-%m', date) AS month, SUM(amount) FROM transactions WHERE user_id = ? GROUP BY month", (user_id,))
        data = c.fetchall()
        conn.close()

        # Format data for Chart.js
        labels = [datetime.strptime(row[0], '%Y-%m').strftime('%b %Y') for row in data]
        amounts = [row[1] for row in data]

        return jsonify({'labels': labels, 'amounts': amounts})
    else:
        return redirect(url_for('login'))
    
    
from flask import session

@app.route('/statistics')
def statistics():
    user_id = session.get('user_id')  # Assuming user ID is stored in the session

    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Total expenses
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
    total_expenses = c.fetchone()[0] or 0

    # Expense by category
    c.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE user_id = ?
        GROUP BY category
    """, (user_id,))
    expense_by_category_result = c.fetchall()
    expense_by_category = dict(expense_by_category_result)

    # Top spending categories
    c.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE user_id = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
        LIMIT 5
    """, (user_id,))
    top_spending_categories = dict(c.fetchall())

    # Monthly expenses (e.g., 2025-04)
    c.execute("""
        SELECT strftime('%Y-%m', date) AS month, SUM(amount)
        FROM transactions
        WHERE user_id = ?
        GROUP BY month
        ORDER BY month
    """, (user_id,))
    monthly_expenses = dict(c.fetchall())

    # Yearly expenses (e.g., 2025)
    c.execute("""
        SELECT strftime('%Y', date) AS year, SUM(amount)
        FROM transactions
        WHERE user_id = ?
        GROUP BY year
        ORDER BY year
    """, (user_id,))
    yearly_expenses = dict(c.fetchall())

    # Top payment methods
    c.execute("""
        SELECT payment_method, SUM(amount)
        FROM transactions
        WHERE user_id = ?
        GROUP BY payment_method
        ORDER BY SUM(amount) DESC
        LIMIT 5
    """, (user_id,))
    top_payment_methods = dict(c.fetchall())

    # Daily trend
    c.execute("""
        SELECT date, SUM(amount)
        FROM transactions
        WHERE user_id = ?
        GROUP BY date
        ORDER BY date
    """, (user_id,))
    daily_spending = dict(c.fetchall())

    # Count of transactions by category
    c.execute("""
        SELECT category, COUNT(*)
        FROM transactions
        WHERE user_id = ?
        GROUP BY category
    """, (user_id,))
    expense_count_by_category = dict(c.fetchall())

    # Average spending per transaction
    c.execute("SELECT AVG(amount) FROM transactions WHERE user_id = ?", (user_id,))
    avg_spending = c.fetchone()[0] or 0

    conn.close()

    return render_template('statistics.html',
                           total_expenses=total_expenses,
                           expense_by_category=expense_by_category,
                           top_spending_categories=top_spending_categories,
                           monthly_expenses=monthly_expenses,
                           yearly_expenses=yearly_expenses,
                           top_payment_methods=top_payment_methods,
                           daily_spending=daily_spending,
                           expense_count_by_category=expense_count_by_category,
                           avg_spending=avg_spending)

if __name__ == '__main__':
    app.run(debug=True)