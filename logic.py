import csv
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
import os # Added os for file existence check and renaming

# Function to save all clients to users.txt
def save_all_clients(clients):
    """Saves the state of all client objects to users.txt."""
    try:
        # Using a temporary file for safer writing
        temp_file = "users.txt.tmp"
        with open(temp_file, "w", newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(["username", "password", "amount", "budget", "total_spent", "loans", "recurring"])

            for client in clients:
                # Format recurring list into a string: amount|category|freq|last_time;amount2|...
                # Ensure last_time is formatted as a string
                recurring_str = ";".join([
                    f"{item[0]}|{item[1]}|{item[2]}|{item[3].strftime('%Y-%m-%d %H:%M:%S')}"
                    for item in client.recurring
                ])
                writer.writerow([
                    client.uname,
                    client.password,
                    client.amount,
                    client.budget,
                    client.total_spent,
                    client.loans,
                    recurring_str
                ])

        # Replace the old file with the new one atomically
        os.replace(temp_file, "users.txt")
        # print("Clients saved successfully.") # Debug print
    except Exception as e:
        print(f"Error saving users to file: {e}") # Debug print

# Function to load all clients from users.txt
def load_all_clients():
    """Loads all client data from users.txt"""
    clients = []
    if not os.path.exists("users.txt"):
        print("users.txt not found. Starting with no users.")
        return clients # Return empty list if file doesn't exist

    try:
        with open("users.txt", "r") as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header row

            for row in reader:
                # Ensure row has the expected number of columns (at least 7)
                if len(row) >= 7:
                    try:
                        uname, pw, amount_str, budget_str, total_spent_str, loans_str, recurring_str = row
                        amount = float(amount_str)
                        budget = float(budget_str)
                        total_spent = float(total_spent_str)
                        loans = float(loans_str)

                        # Parse recurring string
                        recurring = []
                        if recurring_str:
                            recurring_items = recurring_str.split(";")
                            for item_str in recurring_items:
                                parts = item_str.split("|")
                                if len(parts) == 4:
                                    try:
                                        rec_amount = float(parts[0])
                                        rec_category = parts[1]
                                        rec_freq = int(parts[2])
                                        # Convert timestamp string back to datetime object
                                        rec_last_time = datetime.strptime(parts[3], '%Y-%m-%d %H:%M:%S')
                                        recurring.append((rec_amount, rec_category, rec_freq, rec_last_time))
                                    except (ValueError, IndexError):
                                        print(f"Skipping malformed recurring item during load: {item_str}")
                                else:
                                     print(f"Skipping malformed recurring item parts during load: {item_str}")


                        # Assuming StandardAccount for all loaded users for simplicity.
                        # If account type needs to be preserved, it should be added to the file format.
                        client = StandardAccount(uname, pw, amount)
                        client.set_budget(budget) # Use the setter
                        client.total_spent = total_spent # Load saved state
                        client.loans = loans           # Load saved state
                        client.recurring = recurring     # Load saved state
                        clients.append(client)

                    except ValueError:
                        print(f"Skipping invalid row in users.txt (data conversion error): {row}")
                    except IndexError:
                         print(f"Skipping malformed row in users.txt (too few columns): {row}")
                    except Exception as e:
                        print(f"Error processing row in users.txt '{row}': {e}")
                else:
                    print(f"Skipping malformed row in users.txt (incorrect column count): {row}")

    except Exception as e:
        print(f"Failed to load users: {e}")

    return clients


class Client(ABC):
    def __init__(self, username, password, amount):
        self.uname = username.lower()
        self.password = str(password)  # No hashing for simplicity - Consider adding hashing in production
        self.amount = amount
        # These attributes will be loaded from the file for existing users, default for new
        self.total_spent = 0
        self.budget = 0
        self.loans = 0
        self.recurring = []  # list of (amount, category, frequency_days, last_processed_datetime)

    def validate_pass(self, password):
        return self.password == str(password)

    def set_budget(self, budget):
        if budget >= 0:
            self.budget = budget
            # Saving will be handled by the calling GUI function
            return f"✅ Budget set to {budget:.2f}" # Added return for GUI feedback, format budget
        else:
            return "❌ Budget cannot be negative." # Added error return

    def add_income(self, amount):
        if amount <= 0:
            return "❌ Invalid income amount. Amount must be positive."
        self.amount += amount
        self.log_transaction(amount, "Income", "General")
        # Saving will be handled by the calling GUI function
        return f"✅ Income of {amount:.2f} added. Current Balance: {self.amount:.2f}" # Format amounts

    def withdraw(self, amount, category):
        if amount <= 0:
            return "❌ Invalid expense amount. Amount must be positive."
        if amount > self.amount:
            return "❌ Insufficient funds!"

        budget_alert = False
        if self.budget > 0 and (self.total_spent + amount) > self.budget:
             budget_alert = True

        self.amount -= amount
        self.total_spent += amount
        self.log_transaction(amount, "Expense", category)

        # Saving will be handled by the calling GUI function

        if budget_alert:
             return f"⚠️ Withdrawn: {amount:.2f} in category '{category}'. You are now over budget! Remaining Balance: {self.amount:.2f}"
        else:
             return f"✅ Withdrawn: {amount:.2f} in category '{category}'. Remaining Balance: {self.amount:.2f}" # Format amounts

    def transfer(self, receiver, amount):
        if amount <= 0:
            return "❌ Invalid transfer amount. Amount must be positive."
        if self.amount < amount:
            return "❌ Insufficient funds for transfer."
        # Prevent transfer to self handled in GUI

        self.amount -= amount
        receiver.amount += amount
        self.log_transaction(amount, "Transfer Out", receiver.uname)
        receiver.log_transaction(amount, "Transfer In", self.uname)

        # Saving will be handled by the calling GUI function for both sender and receiver state

        return f"✅ Transferred {amount:.2f} to {receiver.uname}. Remaining Balance: {self.amount:.2f}" # Format amounts

    def request_loan(self, amount):
        if amount <= 0:
            return "❌ Invalid loan amount. Amount must be positive."
        # Added simple eligibility checks
        if self.amount < 100 and self.loans == 0: # Check minimum balance only if no existing loan
             return "❌ Not eligible for loan. Maintain a minimum balance of PKR 100."
        if self.loans > 0 and amount > self.loans * 2 and self.loans > 500: # Prevent excessive new loans if one exists and is substantial
             return "❌ Cannot take a new loan more than double your current outstanding loan."


        self.amount += amount
        self.loans += amount
        self.log_transaction(amount, "Loan Received", "Bank")

        # Saving will be handled by the calling GUI function

        return f"✅ Loan of {amount:.2f} approved. Current Outstanding Loan: {self.loans:.2f}" # Format amounts

    def repay_loan(self, amount):
        if amount <= 0:
            return "❌ Invalid repayment amount. Amount must be positive."
        if amount > self.amount:
            return "❌ Insufficient funds."
        if amount > self.loans:
            # Allow repaying less than the outstanding loan, but not more
            return f"❌ Cannot repay more than the outstanding loan amount ({self.loans:.2f})."

        self.amount -= amount
        self.loans -= amount
        self.log_transaction(amount, "Loan Repayment", "Bank")

        # Saving will be handled by the calling GUI function

        return f"✅ Repaid {amount:.2f} towards loan. Remaining Loan: {self.loans:.2f}" # Format amounts


    def schedule_recurring(self, amount, category, frequency_days):
        if amount <= 0 or frequency_days <= 0:
            return "❌ Invalid amount or frequency for recurring expense. Both must be positive."
        # Store amount, category, frequency, and the datetime it was scheduled or last processed
        self.recurring.append((amount, category, frequency_days, datetime.now()))
        # Saving will be handled by the calling GUI function
        return f"✅ Recurring expense of {amount:.2f} '{category}' scheduled every {frequency_days} days." # Format amount


    def process_recurring(self):
        """Processes overdue recurring transactions and logs them. Updates recurring list."""
        # This method modifies self.amount, self.total_spent, and self.recurring
        # It should be called upon login and potentially periodically while the app is open
        # The changes need to be saved *after* processing in the calling GUI code.
        today = datetime.now()
        new_list = []
        processed_count = 0
        log_entries = [] # Collect transactions to log together

        for amount, category, freq, last_time in self.recurring:
            # Calculate days passed. Handle potential future last_time if clock was adjusted back.
            days_passed = max(0, (today - last_time).days)

            if days_passed >= freq:
                # Determine how many occurrences are overdue
                num_occurrences = days_passed // freq

                for i in range(num_occurrences):
                     # Calculate the timestamp for this specific occurrence
                     occurrence_time = last_time + timedelta(days=(i + 1) * freq)

                     # Use a simplified withdrawal logic here for recurring
                     # Check if funds are sufficient *for this occurrence*
                     if self.amount >= amount:
                         self.amount -= amount
                         self.total_spent += amount
                         # Collect transaction details to log later
                         log_entries.append((self.uname, occurrence_time.strftime("%Y-%m-%d %H:%M:%S"), amount, "Recurring Expense", category))
                         processed_count += 1
                     else:
                         print(f"Warning: Insufficient funds ({self.amount:.2f}) for recurring expense {amount:.2f} '{category}'. Skipping this occurrence.")
                         # Optionally log failed recurring transaction
                         log_entries.append((self.uname, occurrence_time.strftime("%Y-%m-%d %H:%M:%S"), amount, "Recurring Expense Failed", category)) # Log failure

                # Update last_time for the next cycle based on the last processed occurrence
                last_processed_date = last_time + timedelta(days=num_occurrences * freq)
                new_list.append((amount, category, freq, last_processed_date))
            else:
                # Not overdue, keep the item as is
                new_list.append((amount, category, freq, last_time))

        self.recurring = new_list # Update the recurring list

        # Log all processed transactions for this user at once
        if log_entries:
            try:
                with open("transactions.csv", "a", newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(log_entries)
                print(f"Logged {len(log_entries)} recurring transaction occurrences for {self.uname}.") # Debug print
            except Exception as e:
                 print(f"Error logging recurring transactions for user {self.uname}: {e}") # Debug print


        if processed_count > 0:
            print(f"Processed {processed_count} recurring transactions (successful/failed) for {self.uname}.") # Debug print


    def display_balance(self):
        # Returning raw number, formatting done in GUI
        return self.amount

    def display_budget(self):
         # Returning raw number, formatting done in GUI
        return self.budget

    def remaining_amount(self):
        # Calculation done here, formatting in GUI
        return self.budget - self.total_spent if self.budget > 0 else "No budget set"

    # Removed the old save_to_file method from the class

    def log_transaction(self, amount, t_type, category):
        """Logs a single transaction to transactions.csv."""
        try:
            with open("transactions.csv", "a", newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    self.uname,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    amount,
                    t_type,
                    category
                ])
        except Exception as e:
            print(f"Error logging transaction for user {self.uname} ({t_type}): {e}") # Debug print


class StandardAccount(Client):
    # Inherits all methods from Client. Specific overrides for restrictions.
    pass

class ChildAccount(Client):
    # Override restricted methods
    def request_loan(self, amount):
        return "❌ Loan not available for child accounts."

    def transfer(self, receiver, amount):
        return "❌ Transfers not allowed for child accounts."

    # Child accounts can set budget and have expenses/income, no specific overrides needed unless restrictions apply


# Moved functions that operate on the list of clients or files outside the class

def create_client(clients, username, password, initial_amount, account_type="standard"):
    """Creates a new client, adds them to the clients list, and saves all clients."""
    # Basic input validation
    if not username or not password:
        return "❌ Username and password cannot be empty."
    if initial_amount < 0:
         return "❌ Initial amount cannot be negative."

    # Check if username already exists (case-insensitive)
    if any(client.uname == username.lower() for client in clients):
        return "❌ Username already exists."

    # Determine account type and create the client object
    if account_type.lower() == "child":
        new_client = ChildAccount(username, password, initial_amount)
    else: # Default to standard if type is invalid or not provided
        new_client = StandardAccount(username, password, initial_amount)

    # Add the new client to the in-memory list
    clients.append(new_client)

    # Save the entire list of clients to persist the new user
    save_all_clients(clients)

    return f"✅ Account '{username}' created successfully!"


def validate(clients, name, password):
    """Validates user credentials against the list of clients loaded in memory."""
    # Find the client by username (case-insensitive)
    client = find_client_by_username(clients, name)

    if client and client.validate_pass(password):
        return clients.index(client) # Return index if found and password matches
    return None # Return None if user not found or password incorrect

# Helper function to find a client by username
def find_client_by_username(clients, username):
    """Finds a client object in the list by username (case-insensitive)."""
    for client in clients:
        if client.uname == username.lower():
            return client
    return None


def generate_report(username):
    """Generates a basic financial report for a user from transaction data."""
    try:
        df = pd.read_csv("transactions.csv")
        user_data = df[df["username"] == username.lower()].copy() # Use .copy()

        if user_data.empty:
            return "No transaction data available for this user."

        # Ensure amount is numeric
        user_data['amount'] = pd.to_numeric(user_data['amount'], errors='coerce').fillna(0)

        # Define inflow and outflow types more explicitly
        inflow_types = ["Income", "Loan Received", "Transfer In"]
        outflow_types = ["Expense", "Loan Repayment", "Transfer Out", "Recurring Expense", "Recurring Expense Failed"]

        income = user_data[user_data["type"].isin(inflow_types)]["amount"].sum()
        expense = user_data[user_data["type"].isin(outflow_types)]["amount"].sum()

        net_flow = income - expense

        report = f"--- Financial Activity Summary for {username.title()} ---\n"
        report += f"Total Inflow (Income, Loans, Transfers In): {income:.2f}\n"
        report += f"Total Outflow (Expenses, Loan Repayments, Transfers Out, Recurring): {expense:.2f}\n"
        report += f"Net Cash Flow: {net_flow:.2f}\n"

        # Add expense breakdown by category
        expense_data = user_data[user_data["type"].isin(['Expense', 'Recurring Expense'])].copy()
        if not expense_data.empty:
            category_breakdown = expense_data.groupby('category')['amount'].sum().sort_values(ascending=False)
            if not category_breakdown.empty:
                report += "\nExpense Breakdown by Category:\n"
                for category, total in category_breakdown.items():
                    report += f"- {category}: {total:.2f}\n"
        else:
            report += "\nNo detailed expense breakdown available."


        return report

    except FileNotFoundError:
        return "Transaction data file not found."
    except pd.errors.EmptyDataError:
         return "Transaction data file is empty."
    except Exception as e:
        print(f"Error generating report for {username}: {e}") # Debug print
        return f"Error generating report: {e}"


def plot_charts(username):
    """Generates and saves monthly trend and expense pie charts for a user."""
    monthly_path = f"{username.lower()}_monthly_trend.png"
    pie_path = f"{username.lower()}_expense_pie.png"

    # Ensure matplotlib does not try to open a GUI window
    plt.switch_backend('Agg')

    try:
        df = pd.read_csv("transactions.csv")
        df_user = df[df['username'] == username.lower()].copy() # Use .copy() to avoid SettingWithCopyWarning

        if df_user.empty:
            # Remove old chart files if no data exists or error occurs
            if os.path.exists(monthly_path): os.remove(monthly_path)
            if os.path.exists(pie_path): os.remove(pie_path)
            print(f"No transaction data to plot for {username}. Removed old chart files.")
            # Return a message or raise a specific error if GUI needs to know
            # For now, rely on GUI checking for file existence
            return

        # Ensure necessary columns exist and have correct data types
        if 'timestamp' not in df_user.columns or 'amount' not in df_user.columns or 'type' not in df_user.columns or 'category' not in df_user.columns:
            print(f"Missing required columns in transactions.csv for user {username}.")
            if os.path.exists(monthly_path): os.remove(monthly_path)
            if os.path.exists(pie_path): os.remove(pie_path)
            # Return or raise error
            return

        df_user["timestamp"] = pd.to_datetime(df_user["timestamp"], errors='coerce')
        df_user.dropna(subset=['timestamp'], inplace=True) # Remove rows with invalid timestamps
        df_user["amount"] = pd.to_numeric(df_user["amount"], errors='coerce').fillna(0) # Convert amount to numeric, fill errors with 0


        # --- Monthly Trend ---
        # Calculate net monthly flow
        monthly_flow = df_user.copy()
        # Convert outflow amounts to negative for net flow calculation
        outflow_types = ["Expense", "Loan Repayment", "Transfer Out", "Recurring Expense", "Recurring Expense Failed"]
        monthly_flow.loc[monthly_flow['type'].isin(outflow_types), 'amount'] *= -1

        # Resample monthly and sum the amounts
        monthly = monthly_flow.resample("M", on="timestamp")["amount"].sum().sort_index()

        plt.figure(figsize=(10, 6))
        plt.plot(monthly.index, monthly.values, marker='o', linestyle='-')
        plt.title(f"{username.title()}'s Monthly Net Cash Flow")
        plt.xlabel("Month")
        plt.ylabel("Amount (PKR)")
        plt.grid(True)
        plt.xticks(rotation=45, ha='right') # Rotate labels and align them to the right
        plt.tight_layout() # Adjust layout to prevent labels overlapping
        plt.savefig(monthly_path)
        plt.close() # Close the plot figure to free memory


        # --- Expense Pie Chart ---
        # Only include actual expenses and recurring expenses for pie chart
        expense_data = df_user[df_user["type"].isin(['Expense', 'Recurring Expense'])].copy()

        if expense_data.empty:
             if os.path.exists(pie_path): os.remove(pie_path)
             print(f"No actual expense data to plot pie chart for {username}. Removed old pie chart file.")
             return # Exit if no expense data

        # Group by category and sum amounts
        pie_data = expense_data.groupby("category")["amount"].sum().sort_values(ascending=False)

        # Filter out categories with zero total expense
        pie_data = pie_data[pie_data > 0]

        if pie_data.empty:
             if os.path.exists(pie_path): os.remove(pie_path)
             print(f"Expense data exists but all categories have zero total for {username}. Removed old pie chart file.")
             return

        plt.figure(figsize=(8, 8))
        pie_data.plot.pie(autopct='%1.1f%%', startangle=90)
        plt.title(f"{username.title()}'s Expense Breakdown")
        plt.ylabel("") # Hide default 'amount' label on pie chart
        plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
        plt.tight_layout()
        plt.savefig(pie_path)
        plt.close() # Close the plot figure

        # print(f"Charts generated for {username}.") # Debug print

    except FileNotFoundError:
        print("transactions.csv not found for plotting.") # Debug print
         # Optionally, still remove potentially outdated files
        if os.path.exists(monthly_path): os.remove(monthly_path)
        if os.path.exists(pie_path): os.remove(pie_path)
        raise # Re-raise to be caught by GUI for user feedback
    except pd.errors.EmptyDataError:
        print("transactions.csv is empty for plotting.") # Debug print
        if os.path.exists(monthly_path): os.remove(monthly_path)
        if os.path.exists(pie_path): os.remove(pie_path)
        return # No data, gracefully exit
    except Exception as e:
        print(f"Error generating charts for {username}: {e}") # Debug print
        # Optionally, still remove potentially corrupted/outdated files
        if os.path.exists(monthly_path): os.remove(monthly_path)
        if os.path.exists(pie_path): os.remove(pie_path)
        raise # Re-raise to be caught by GUI for user feedback


def predict_future_expense_data(username, days_to_predict=30):
    """
    Predicts future cumulative expense data points using linear regression.
    Returns a dictionary with historical and predicted data for plotting.
    Also saves the combined plot.
    """
    plot_path = f"{username.lower()}_historical_predicted_expense.png"
    plt.switch_backend('Agg') # Use Agg backend for non-GUI plotting

    try:
        df = pd.read_csv("transactions.csv")
        df_user = df[df["username"] == username.lower()].copy()
        # Only use actual expenses and recurring expenses for prediction
        df_expenses = df_user[df_user["type"].isin(['Expense', 'Recurring Expense'])].copy()

        if df_expenses.shape[0] < 2: # Need at least 2 data points for meaningful linear regression
            # Remove old plot file if not enough data
            if os.path.exists(plot_path): os.remove(plot_path)
            return {"message": "Not enough expense data to make a prediction (need at least 2 expense records)."}

        # Ensure timestamp and amount are in correct formats
        df_expenses["timestamp"] = pd.to_datetime(df_expenses["timestamp"], errors='coerce')
        df_expenses.dropna(subset=['timestamp'], inplace=True) # Remove rows with invalid timestamps
        df_expenses["amount"] = pd.to_numeric(df_expenses["amount"], errors='coerce').fillna(0) # Convert amount to numeric, fill errors with 0

        if df_expenses.empty: # Check again after dropping invalid timestamps/amounts
            if os.path.exists(plot_path): os.remove(plot_path)
            return {"message": "Not enough valid expense data to make a prediction."}


        df_expenses.sort_values("timestamp", inplace=True)

        # Calculate days from the *first* expense timestamp
        first_expense_time = df_expenses["timestamp"].iloc[0]
        df_expenses["days"] = (df_expenses["timestamp"] - first_expense_time).dt.days

        # Use cumulative expense over time for a trend prediction
        df_expenses['cumulative_expense'] = df_expenses['amount'].cumsum()

        # Prepare data for the model
        # X should be the number of days since the first transaction
        X_hist = df_expenses["days"].values.reshape(-1, 1)
        # y should be the cumulative expense up to that day
        y_hist = df_expenses["cumulative_expense"].values

        # If all expenses are on the same day, prediction is not meaningful with this model
        if len(np.unique(X_hist)) < 2:
            if os.path.exists(plot_path): os.remove(plot_path)
            return {"message": "Not enough variation in expense timing to make a prediction."}

        # Train the linear regression model
        model = LinearRegression()
        model.fit(X_hist, y_hist)

        # Generate future days for prediction
        last_day_recorded = X_hist[-1][0]
        future_days = np.arange(last_day_recorded + 1, last_day_recorded + days_to_predict + 1).reshape(-1, 1)

        # Predict cumulative expense for future days
        y_pred = model.predict(future_days)

        # Prepare data for plotting
        # Combine historical and predicted days and values
        combined_days = np.concatenate((X_hist, future_days))
        combined_cumulative_expense = np.concatenate((y_hist, y_pred))

        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(X_hist.flatten(), y_hist, marker='o', linestyle='-', label='Historical Cumulative Expense')
        plt.plot(future_days.flatten(), y_pred, marker='x', linestyle='--', color='red', label=f'Predicted Cumulative Expense ({days_to_predict} days)')

        plt.title(f"{username.title()}'s Historical and Predicted Cumulative Expense")
        plt.xlabel("Days Since First Expense")
        plt.ylabel("Cumulative Expense (PKR)")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        # Save the plot
        plt.savefig(plot_path)
        plt.close() # Close the plot figure

        return {"message": f"Plot saved to {plot_path}", "plot_path": plot_path}

    except FileNotFoundError:
        if os.path.exists(plot_path): os.remove(plot_path)
        return {"message": "Transaction data file not found for prediction."}
    except pd.errors.EmptyDataError:
        if os.path.exists(plot_path): os.remove(plot_path)
        return {"message": "Transaction data file is empty for prediction."}
    except Exception as e:
        print(f"Error during prediction data generation and plotting for {username}: {e}") # Debug print
        if os.path.exists(plot_path): os.remove(plot_path)
        return {"message": f"Error during prediction data generation and plotting: {e}"}


def predict_next_month_expense(username):
    """
    Predicts the total expense for the next calendar month using linear regression.
    Returns a message string with the predicted amount or an error.
    """
    try:
        df = pd.read_csv("transactions.csv")
        df_user = df[df["username"] == username.lower()].copy()
        df_expenses = df_user[df_user["type"].isin(['Expense', 'Recurring Expense'])].copy()

        if df_expenses.shape[0] < 2:
            return "❌ Not enough expense data to predict next month's expense (need at least 2 expense records)."

        df_expenses["timestamp"] = pd.to_datetime(df_expenses["timestamp"], errors='coerce')
        df_expenses.dropna(subset=['timestamp'], inplace=True)
        df_expenses["amount"] = pd.to_numeric(df_expenses["amount"], errors='coerce').fillna(0)

        if df_expenses.empty:
            return "❌ Not enough valid expense data to predict next month's expense."

        df_expenses.sort_values("timestamp", inplace=True)

        # Calculate days from the *first* expense timestamp
        first_expense_time = df_expenses["timestamp"].iloc[0]
        df_expenses["days"] = (df_expenses["timestamp"] - first_expense_time).dt.days

        df_expenses['cumulative_expense'] = df_expenses['amount'].cumsum()

        X_hist = df_expenses["days"].values.reshape(-1, 1)
        y_hist = df_expenses["cumulative_expense"].values

        if len(np.unique(X_hist)) < 2:
             return "❌ Not enough variation in expense timing to predict next month's expense."

        model = LinearRegression()
        model.fit(X_hist, y_hist)

        # Determine the number of days until the end of the current month and the number of days in the next month
        today = datetime.now()
        # Find the first day of the next month
        if today.month == 12:
            first_day_of_next_month = datetime(today.year + 1, 1, 1)
        else:
            first_day_of_next_month = datetime(today.year, today.month + 1, 1)

        # Find the last day of the next month
        if first_day_of_next_month.month == 12:
            last_day_of_next_month = datetime(first_day_of_next_month.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day_of_next_month = datetime(first_day_of_next_month.year, first_day_of_next_month.month + 1, 1) - timedelta(days=1)


        # Calculate the 'days since first expense' for the start and end of the next month
        days_to_start_of_next_month = (first_day_of_next_month - first_expense_time).days
        days_to_end_of_next_month = (last_day_of_next_month - first_expense_time).days

        # Ensure these day counts are not before the last recorded day
        last_recorded_day = X_hist[-1][0]
        days_to_start_of_next_month = max(last_recorded_day, days_to_start_of_next_month)
        days_to_end_of_next_month = max(last_recorded_day, days_to_end_of_next_month)


        # Predict cumulative expense at the start and end of the next month
        predicted_cumulative_start = model.predict(np.array([[days_to_start_of_next_month]]))
        predicted_cumulative_end = model.predict(np.array([[days_to_end_of_next_month]]))

        # The predicted expense for the next month is the difference
        predicted_expense_next_month = predicted_cumulative_end[0] - predicted_cumulative_start[0]

        # Ensure the prediction is not negative
        predicted_expense_next_month = max(0, predicted_expense_next_month)

        # Format the month name for the output message
        next_month_name = first_day_of_next_month.strftime("%B")

        return f"📈 Predicted expense for {next_month_name}: PKR {predicted_expense_next_month:.2f}"

    except FileNotFoundError:
        return "❌ Transaction data file not found for prediction."
    except pd.errors.EmptyDataError:
         return "❌ Transaction data file is empty for prediction."
    except Exception as e:
        print(f"Error during next month prediction for {username}: {e}") # Debug print
        return f"❌ Error during next month prediction: {e}"


def export_user_data(username):
    """Exports a user's transaction data to a CSV file."""
    try:
        df = pd.read_csv("transactions.csv")
        df_user = df[df["username"] == username.lower()].copy()

        if df_user.empty:
             return "No transaction data found to export for this user."

        export_filename = f"{username.lower()}_transactions_export.csv"
        df_user.to_csv(export_filename, index=False)
        return f"✅ Data exported to {export_filename}"

    except FileNotFoundError:
         return "Transaction data file not found for export."
    except pd.errors.EmptyDataError:
         return "Transaction data file is empty for export."
    except Exception as e:
         print(f"Error exporting data for {username}: {e}") # Debug print text
         return f"Error exporting data: {e}"