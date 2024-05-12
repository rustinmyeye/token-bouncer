import subprocess
import json
import time
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# File paths for saving mnemonic, token IDs, and wallet initialization status
MNEMONIC_FILE = 'mnemonic.txt'
TOKEN_IDS_FILE = 'token_ids.txt'
WALLET_INITIALIZED_FILE = 'wallet_initialized.txt'

# Burn address
BURN_ADDRESS = '9gCBhSmzxSUe1KitTVnK1L4ibvkQ7V1pC1XjSokcjVHycyfsBwN'

# Function to run subprocess and return output
def run_subprocess(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode(), error.decode()

# Function to save mnemonic to file and initialize wallet
def save_mnemonic(mnemonic):
    with open(MNEMONIC_FILE, 'w') as file:
        file.write(mnemonic)
    initialize_wallet(mnemonic)
    check_and_bounce_tokens()
    start_token_checking_loop()
    
# Function to save token IDs to file and start the loop for checking and sending tokens
def save_token_ids(token_ids):
    with open(TOKEN_IDS_FILE, 'w') as file:
        for token_id in token_ids:
            file.write(token_id + '\n')

# Function to check if wallet is initialized
def is_wallet_initialized():
    return os.path.exists(WALLET_INITIALIZED_FILE)

# Function to initialize wallet with mnemonic
def initialize_wallet(mnemonic):
    if not is_wallet_initialized():
        command = ['ewc', 'new-wallet', '-n', 'test', '-p', '1234', '-m', mnemonic]
        _, error = run_subprocess(command)
        if error:
            print("Error initializing wallet:", error)
        else:
            with open(WALLET_INITIALIZED_FILE, 'w'):
                pass  # Create empty file to mark wallet as initialized

# Function to get mnemonic from file
def get_mnemonic():
    try:
        with open(MNEMONIC_FILE, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Function to get token IDs from file
def get_token_ids():
    try:
        with open(TOKEN_IDS_FILE, 'r') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        return []

# Function to start the loop for checking and sending tokens
def start_token_checking_loop():
    while True:
        check_and_bounce_tokens()
        time.sleep(5 * 60)  # 5 minutes

# Function to check wallet for tokens and bounce if found
def check_and_bounce_tokens():
    if is_wallet_initialized():
        mnemonic = get_mnemonic()
        token_ids = get_token_ids()

        if not mnemonic or not token_ids:
            return

        command = ['ewc', 'wallet-get', '-b', 'all', 'test', '1234']
        output, error = run_subprocess(command)

        if error:
            print("Error:", error)
            return

        wallet_data = json.loads(output)
        tokens = wallet_data.get('tokens', [])

        for token in tokens:
            if token['tokenId'] in token_ids:
                # Bounce token
                token_amount = token['amount'].replace(',', '')  # Remove comma
                process = subprocess.Popen(['ewc', 'wallet-send', '-e', '0.0001', '-t', token['tokenId'], '-u', token_amount, '-a', BURN_ADDRESS, 'test', '1234', '--sign', '--send'], stdin=subprocess.PIPE)
                process.communicate(input=b'y\n')  # Send "y" to confirm the transaction
                print("Token bounced:", token['tokenId'])

# Route for home page
@app.route('/')
def home():
    mnemonic = get_mnemonic()
    token_ids = get_token_ids()
    return render_template('index.html', mnemonic=mnemonic, token_ids=token_ids)

# Route to set mnemonic
@app.route('/set_mnemonic', methods=['POST'])
def set_mnemonic():
    mnemonic = request.form['mnemonic']
    save_mnemonic(mnemonic)
    return redirect(url_for('home'))

# Route to set token IDs
@app.route('/set_token_ids', methods=['POST'])
def set_token_ids():
    token_ids = request.form.getlist('token_ids')
    save_token_ids(token_ids)
    return redirect(url_for('home'))

# Route to reset mnemonic
@app.route('/reset_mnemonic', methods=['POST'])
def reset_mnemonic():
    subprocess.run(['rm', 'ewc/build/wallets/test.wallet'])
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
