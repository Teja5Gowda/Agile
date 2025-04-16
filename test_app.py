import pytest
import sqlite3
from app import app, init_db, DATABASE

@pytest.fixture
def client():
    init_db()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_index_redirects_if_not_logged_in(client):
    response = client.get('/')
    assert response.status_code == 302
    assert '/login' in response.location

def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data  # assuming login.html has the word "Login"

def test_register_page_loads(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data  # assuming register.html has "Register"

def test_register_and_login(client):
    # Register a user
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'phone': '1234567890',
        'password': 'testpass'
    }, follow_redirects=True)

    # Check if the user is redirected to the login page after successful registration
    assert b'Login' in response.data  # Check if 'Login' is in the page, indicating the login page is loaded

    # Login with the registered user
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    }, follow_redirects=True)

    # Decode response.data to string and check if 'total_amount' or 'Welcome' is in the response
    response_data = response.data.decode()
    assert 'total_amount' in response_data or 'Welcome' in response_data

def test_add_transaction_requires_login(client):
    response = client.post('/add_transaction', data={
        'date': '2025-04-15',
        'category': 'Food',
        'amount': '100',
        'payment_method': 'UPI',
        'notes': 'Lunch'
    })
    assert response.status_code == 302
    assert '/login' in response.location

def test_statistics_redirects_if_not_logged_in(client):
    response = client.get('/statistics')
    assert response.status_code == 302
    assert '/login' in response.location
