# --- Redesigned Finance Manager App using CustomTkinter ---

import customtkinter as ctk
from tkinter import messagebox, Toplevel, PhotoImage # Added Toplevel and PhotoImage
import csv # Added import for csv module
# Import specific functions and classes from logic
from logic import (
    create_client, validate, StandardAccount, ChildAccount,
    generate_report, plot_charts, predict_future_expense_data, predict_next_month_expense, export_user_data, # Changed import here
    load_all_clients, save_all_clients, find_client_by_username # Import new/modified functions
)
# Removed "import logic" as specific functions are imported
from PIL import Image, ImageTk # For displaying graphs
import pandas as pd
import os # To check if files exist
# import numpy as np # numpy is used in logic, no need to import here unless used in GUI

# --- Theme Colors (Refined) ---
PRIMARY_DARK = "#1A1A2E" # Darker Navy Blue
SECONDARY_DARK = "#16213E" # Slightly lighter Navy/Indigo
TERTIARY_DARK = "#0F3460" # Sidebar Active/Hover
ACCENT_PURPLE = "#8A4EFC" # Keeping accents vibrant
ACCENT_PINK = "#FC4EA3"
ACCENT_BLUE = "#53D8FB" # Brighter Blue
ACCENT_GREEN = "#76E2B3" # Green for Income/Success
ACCENT_RED = "#F95A7E" # Red for Expenses/Errors
TEXT_LIGHT = "#EAEAEA"
TEXT_ACCENT = "#FFFFFF"
ENTRY_FIELD = "#2A2F4F" # Adjusted Entry Field
PROGRESS_BAR = ACCENT_BLUE # Green or Blue for progress? Let's stick to Blue as in original.

ctk.set_appearance_mode("Dark")

# --- Main Application Setup ---
app = ctk.CTk()
app.geometry("1200x750") # Slightly larger window
app.title("X-Analytics - Personal Finance Manager")
app.configure(fg_color=PRIMARY_DARK)

# --- Global Variables ---
clients = [] # This list will now hold all client objects loaded from the file
current_user = None # Will hold the logged-in Client object
# Global variable to hold the prediction image reference to prevent garbage collection
prediction_img_label = None


# --- Utility Functions ---
def format_currency(amount):
    """Formats a number as PKR currency."""
    try:
        # Ensure amount is a number before formatting
        if amount is None or not isinstance(amount, (int, float)):
            return "PKR 0.00"
        return "PKR {:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return "PKR 0.00"

def ensure_transaction_file():
    """Creates transactions.csv with headers if it doesn't exist."""
    # csv module is now imported at the top
    if not os.path.exists("transactions.csv"):
        try:
            with open("transactions.csv", "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["username", "timestamp", "amount", "type", "category"])
            print("Created transactions.csv with headers.") # Debug print
        except Exception as e:
            print(f"Error creating transactions.csv: {e}") # Debug print


# --- Initial Load Users (Only call once at startup) ---
def load_initial_users():
    """Loads user data from users.txt at application startup."""
    global clients
    clients = load_all_clients() # Use the new function from logic.py
    # print(f"Loaded {len(clients)} users initially.") # Debug print
    # Recurring transactions will be processed for the logged-in user on login.

# --- Main Content Area Setup ---
main_content = ctk.CTkFrame(app, fg_color=PRIMARY_DARK, corner_radius=0)
main_content.pack(side="right", expand=True, fill="both")

# --- Content Frames Dictionary ---
content_frames = {}

def switch_view(name):
    """Hides all frames and shows the selected one, updating it."""
    global current_user
    # Allow switching to Register view even if not logged in
    if not current_user and name not in ["Login", "Register"]:
        messagebox.showwarning("Auth Required", "Please log in first.")
        return

    # Save current user state before switching views (if logged in and not switching to Login/Register)
    # This provides an extra layer of saving, besides saving after each operation
    if current_user and name not in ["Login", "Register"]:
         save_all_clients(clients) # Save state before leaving an authenticated view
         print("Saving state on view switch.") # Debug print


    # Hide all frames
    for frame in content_frames.values():
        frame.pack_forget()
        # Also hide the sub-frames for login/register if they are currently placed
        if frame == auth_frame:
             login_sub_frame.place_forget() # Use place_forget if placed
             register_sub_frame.place_forget() # Use place_forget if placed


    # Show the selected frame and call its update function
    if name in content_frames:
        content_frames[name].pack(fill="both", expand=True, padx=20, pady=20)

        # Special handling for the auth_frame to show the correct sub-frame
        if name == "Login":
             show_login() # Call helper to show login sub-frame
        elif name == "Register":
             show_register() # Call helper to show register sub-frame


        # Call update function for the specific view if it exists and it's not the auth frame
        if name not in ["Login", "Register"]:
            update_func_name = f"update_{name.lower().replace(' ', '_')}_view"
            if hasattr(app, update_func_name):
                getattr(app, update_func_name)() # Call the update function
            else:
                 print(f"Warning: Update function '{update_func_name}' not found for view '{name}'.")


    else:
        print(f"Error: View '{name}' not found in content_frames.")


# --- Sidebar ---
sidebar = ctk.CTkFrame(app, width=220, fg_color=SECONDARY_DARK, corner_radius=0)
# Sidebar will be packed later after login

# sidebar_buttons = {} # Dictionary to potentially store button references

def add_sidebar_button(name, label, icon_char):
    """Adds a button to the sidebar."""
    button = ctk.CTkButton(sidebar, text=f"{icon_char}  {label}", width=180, height=40,
                           fg_color="transparent", text_color=TEXT_LIGHT,
                           hover_color=TERTIARY_DARK, font=("Arial", 14, "bold"),
                           anchor="w", command=lambda n=name: switch_view(n))
    button.pack(pady=6, padx=10)
    # sidebar_buttons[name] = button # Store button reference if needed for styling active state

def create_sidebar():
    """Creates all sidebar buttons."""
    # Clear existing buttons if any (e.g., on re-login)
    for widget in sidebar.winfo_children():
        widget.destroy()

    ctk.CTkLabel(sidebar, text="X-Analytics", font=("Arial", 20, "bold"), text_color=ACCENT_PURPLE).pack(pady=20, padx=10)

    # Authenticated views
    add_sidebar_button("Dashboard", "Dashboard", "🏠")
    add_sidebar_button("Income", "Income", "➕")
    add_sidebar_button("Expense", "Expense", "➖")
    add_sidebar_button("Transfer", "Transfer", "🔁")
    add_sidebar_button("Loans", "Loans", "💰")
    add_sidebar_button("Budget", "Budget", "🎯")
    # add_sidebar_button("Recurring", "Recurring", "🔄") # Add if logic is extended
    add_sidebar_button("Graphs", "Graphs", "📊")
    add_sidebar_button("AI Overview", "AI Overview", "🤖")
    add_sidebar_button("Export Data", "Export Data", "💾")

    # Logout button at the bottom
    logout_button = ctk.CTkButton(sidebar, text="🚪  Logout", width=180, height=40,
                                 fg_color="transparent", text_color=ACCENT_RED,
                                 hover_color=TERTIARY_DARK, font=("Arial", 14, "bold"),
                                 anchor="w", command=handle_logout)
    logout_button.pack(pady=(20,10), padx=10, side="bottom")


# --- LOGIN / REGISTER VIEW ---
auth_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Login"] = auth_frame # Use the same auth_frame for both Login and Register views
content_frames["Register"] = auth_frame


# --- Login Sub-Frame (Part of auth_frame) ---
login_sub_frame = ctk.CTkFrame(auth_frame, fg_color=SECONDARY_DARK, corner_radius=15)
# Place this when needed using .place() or .pack()

ctk.CTkLabel(login_sub_frame, text="X-Analytics", font=("Arial", 36, "bold"), text_color=ACCENT_PURPLE).pack(pady=(30, 5), padx=50)
ctk.CTkLabel(login_sub_frame, text="Welcome Back!", font=("Arial", 18), text_color=TEXT_LIGHT).pack(pady=(0, 20), padx=50)

ctk.CTkLabel(login_sub_frame, text="Username:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=40, anchor="w") # Added label
login_user_entry = ctk.CTkEntry(login_sub_frame, placeholder_text="Enter Username", width=280, height=35, corner_radius=10, fg_color=ENTRY_FIELD, border_width=0)
login_user_entry.pack(pady=(0, 7), padx=40) # Adjusted padding

ctk.CTkLabel(login_sub_frame, text="Password:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=40, anchor="w") # Added label
login_pass_entry = ctk.CTkEntry(login_sub_frame, placeholder_text="Enter Password", show="*", width=280, height=35, corner_radius=10, fg_color=ENTRY_FIELD, border_width=0)
login_pass_entry.pack(pady=(0, 7), padx=40) # Adjusted padding


def handle_login():
    """Handles the login process."""
    global current_user
    # User list is loaded once on startup. No need to reload here.

    uname = login_user_entry.get().strip() # Use strip() to remove leading/trailing whitespace
    pw = login_pass_entry.get()

    if not uname or not pw:
        messagebox.showerror("Login Error", "Username and Password cannot be empty.")
        return

    # Validate against the clients list already loaded in memory
    user_index = validate(clients, uname, pw)

    if user_index is not None:
        current_user = clients[user_index]
        # Process recurring tasks for the logged-in user immediately after login
        current_user.process_recurring()
        # Save the state after processing recurring transactions
        save_all_clients(clients)


        # Ensure transaction file exists (redundant if logic saves correctly, but safe)
        ensure_transaction_file()

        # Clear fields
        login_user_entry.delete(0, 'end')
        login_pass_entry.delete(0, 'end')

        # Hide auth frame, show sidebar and main content area
        auth_frame.pack_forget() # Hide the main auth frame container
        sidebar.pack(side="left", fill="y") # Pack sidebar now
        create_sidebar() # Create buttons after login (clears existing first)
        switch_view("Dashboard") # Go to dashboard and trigger its update
        messagebox.showinfo("Login Success", f"Welcome back, {current_user.uname.title()}!")
    else:
        messagebox.showerror("Login Failed", "Invalid username or password.")

ctk.CTkButton(login_sub_frame, text="Login", command=handle_login, width=280, height=40, fg_color=ACCENT_PURPLE, hover_color=ACCENT_PINK, font=("Arial", 14, "bold"), corner_radius=10).pack(pady=20, padx=40)


# --- Registration Sub-Frame (Part of auth_frame) ---
register_sub_frame = ctk.CTkFrame(auth_frame, fg_color=SECONDARY_DARK, corner_radius=15)
# This frame will be placed/packed when needed by show_register()

ctk.CTkLabel(register_sub_frame, text="Create Account", font=("Arial", 36, "bold"), text_color=ACCENT_GREEN).pack(pady=(30, 5), padx=50)
ctk.CTkLabel(register_sub_frame, text="Join X-Analytics today!", font=("Arial", 18), text_color=TEXT_LIGHT).pack(pady=(0, 20), padx=50)

# Add labels for registration fields
ctk.CTkLabel(register_sub_frame, text="Username:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=40, anchor="w") # Added label
reg_user_entry = ctk.CTkEntry(register_sub_frame, placeholder_text="Enter Username", width=280, height=35, corner_radius=10, fg_color=ENTRY_FIELD, border_width=0)
reg_user_entry.pack(pady=(0, 7), padx=40) # Adjusted padding

ctk.CTkLabel(register_sub_frame, text="Password:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=40, anchor="w") # Added label
reg_pass_entry = ctk.CTkEntry(register_sub_frame, placeholder_text="Enter Password", show="*", width=280, height=35, corner_radius=10, fg_color=ENTRY_FIELD, border_width=0)
reg_pass_entry.pack(pady=(0, 7), padx=40) # Adjusted padding

ctk.CTkLabel(register_sub_frame, text="Initial Amount:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=40, anchor="w") # Added label
reg_initial_amount_entry = ctk.CTkEntry(register_sub_frame, placeholder_text="e.g., 1000.00", width=280, height=35, corner_radius=10, fg_color=ENTRY_FIELD, border_width=0)
reg_initial_amount_entry.pack(pady=(0, 7), padx=40) # Adjusted padding

# Account Type Selection (Simple example using radio buttons)
ctk.CTkLabel(register_sub_frame, text="Account Type:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(10, 0), padx=40, anchor="w") # Added label for radio buttons
account_type_var = ctk.StringVar(value="standard") # Default value
type_frame = ctk.CTkFrame(register_sub_frame, fg_color="transparent")
type_frame.pack(pady=(0, 10), padx=40, anchor="w") # Adjusted padding

ctk.CTkRadioButton(type_frame, text="Standard", variable=account_type_var, value="standard", text_color=TEXT_LIGHT, fg_color=ACCENT_PURPLE, hover_color=ACCENT_PINK).pack(side="left", padx=5)
ctk.CTkRadioButton(type_frame, text="Child", variable=account_type_var, value="child", text_color=TEXT_LIGHT, fg_color=ACCENT_PURPLE, hover_color=ACCENT_PINK).pack(side="left", padx=5)


def handle_register():
    """Handles the user registration process."""
    uname = reg_user_entry.get().strip()
    pw = reg_pass_entry.get().strip()
    initial_amount_str = reg_initial_amount_entry.get().strip()
    account_type = account_type_var.get()

    # Basic validation before calling logic function
    if not uname or not pw or not initial_amount_str:
        messagebox.showerror("Registration Error", "Username, Password, and Initial Amount cannot be empty.")
        return

    try:
        initial_amount = float(initial_amount_str)
    except ValueError:
        messagebox.showerror("Registration Error", "Please enter a valid number for Initial Amount.")
        return

    # Use create_client from logic.py (which now handles adding to list and saving)
    result_msg = create_client(clients, uname, pw, initial_amount, account_type)

    if "✅" in result_msg:
        messagebox.showinfo("Registration Success", result_msg)
        # Clear fields
        reg_user_entry.delete(0, 'end')
        reg_pass_entry.delete(0, 'end')
        reg_initial_amount_entry.delete(0, 'end')
        account_type_var.set("standard") # Reset default radio button
        switch_view("Login") # Go back to login view after successful registration
    else:
        # create_client returns error messages starting with "❌"
        messagebox.showerror("Registration Failed", result_msg)


ctk.CTkButton(register_sub_frame, text="Create Account", command=handle_register, width=280, height=40, fg_color=ACCENT_GREEN, hover_color=ACCENT_BLUE, font=("Arial", 14, "bold"), corner_radius=10).pack(pady=20, padx=40)

def show_register():
    """Switches to the registration sub-frame within the auth_frame."""
    login_sub_frame.place_forget() # Hide login elements if they are placed
    register_sub_frame.place(relx=0.5, rely=0.5, anchor="center") # Place register frame in the center of auth_frame
    # Clear login fields when switching to register
    if login_user_entry: login_user_entry.delete(0, 'end')
    if login_pass_entry: login_pass_entry.delete(0, 'end')


def show_login():
    """Switches back to the login sub-frame within the auth_frame."""
    register_sub_frame.place_forget() # Hide register elements if they are placed
    login_sub_frame.place(relx=0.5, rely=0.5, anchor="center") # Place login frame in the center of auth_frame
     # Clear registration fields when switching to login
    if reg_user_entry: reg_user_entry.delete(0, 'end')
    if reg_pass_entry: reg_pass_entry.delete(0, 'end')
    if reg_initial_amount_entry: reg_initial_amount_entry.delete(0, 'end')
    account_type_var.set("standard") # Reset radio button


# Add buttons to switch between Login and Register within the auth_frame
ctk.CTkButton(login_sub_frame, text="No Account? Register Here", command=show_register, fg_color="transparent", text_color=TEXT_LIGHT, hover_color=TERTIARY_DARK, font=("Arial", 12)).pack(pady=(0,20))
ctk.CTkButton(register_sub_frame, text="Already have an account? Login Here", command=show_login, fg_color="transparent", text_color=TEXT_LIGHT, hover_color=TERTIARY_DARK, font=("Arial", 12)).pack(pady=(0,20))


# --- ==================== VIEWS (Create frames but pack in switch_view) ==================== ---
# Frames for authenticated views are created here, their content is updated by the update_..._view functions

# --- Dashboard View ---
dashboard_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Dashboard"] = dashboard_frame

def update_dashboard_view():
    """Updates the dashboard with current user data."""
    if not current_user:
        print("update_dashboard_view called with no current user.") # Should not happen if switch_view is correct
        return

    # Clear previous content
    for widget in dashboard_frame.winfo_children():
        widget.destroy()

    # Welcome Message
    ctk.CTkLabel(dashboard_frame, text=f"Welcome, {current_user.uname.title()}!", font=("Arial", 28, "bold"), text_color=TEXT_ACCENT).pack(pady=(10, 5), anchor="w")
    ctk.CTkLabel(dashboard_frame, text="Here's your financial overview:", font=("Arial", 16), text_color=TEXT_LIGHT).pack(pady=(0, 20), anchor="w")

    # --- Top Row: Balance & Budget ---
    top_frame = ctk.CTkFrame(dashboard_frame, fg_color="transparent")
    top_frame.pack(fill="x", pady=10)

    balance_frame = ctk.CTkFrame(top_frame, fg_color=SECONDARY_DARK, corner_radius=10)
    balance_frame.pack(side="left", padx=(0, 10), expand=True, fill="x")
    ctk.CTkLabel(balance_frame, text="Current Balance", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(10, 2), padx=20, anchor="w")
    # Use display_balance which returns the raw number, format in GUI
    ctk.CTkLabel(balance_frame, text=format_currency(current_user.display_balance()), font=("Arial", 24, "bold"), text_color=ACCENT_GREEN).pack(pady=(0, 10), padx=20, anchor="w")

    budget_frame = ctk.CTkFrame(top_frame, fg_color=SECONDARY_DARK, corner_radius=10)
    budget_frame.pack(side="left", padx=(10, 0), expand=True, fill="x")
    ctk.CTkLabel(budget_frame, text="Budget Status", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(10, 2), padx=20, anchor="w")

    budget_val = current_user.display_budget() # Get current budget value
    # Ensure total_spent is a number before calculation
    total_spent_val = current_user.total_spent if isinstance(current_user.total_spent, (int, float)) else 0

    remaining_str = "N/A"
    progress = 0.0 # Represents the portion of budget *spent*
    if budget_val > 0:
        remaining = budget_val - total_spent_val
        remaining_str = format_currency(remaining)
         # Progress is total_spent divided by budget, capped between 0 and 1
        progress = max(0.0, min(1.0, (total_spent_val / budget_val)))
    else:
        remaining_str = "No Budget Set"
        progress = 0.0 # No budget means 0% progress towards it

    ctk.CTkLabel(budget_frame, text=f"Remaining: {remaining_str}", font=("Arial", 18, "bold"), text_color=ACCENT_BLUE).pack(pady=(0, 5), padx=20, anchor="w")

    # Progress bar and percentage display for budget
    budget_prog_bar = ctk.CTkProgressBar(budget_frame, orientation="horizontal", progress_color=PROGRESS_BAR, fg_color=ENTRY_FIELD)
    budget_prog_bar.set(progress) # Set bar value based on spent proportion

    ctk.CTkLabel(budget_frame, text=f"{progress:.1%} Used", font=("Arial", 12), text_color=TEXT_LIGHT).pack(pady=(0, 2), padx=20, anchor="w") # Show percentage
    budget_prog_bar.pack(pady=(0, 10), padx=20, fill="x")

    ctk.CTkLabel(budget_frame, text=f"Total Budget: {format_currency(budget_val)}", font=("Arial", 12), text_color=TEXT_LIGHT).pack(pady=(0, 10), padx=20, anchor="w")


    # --- Bottom Row: Transaction Overview ---
    ctk.CTkLabel(dashboard_frame, text="Recent Activity", font=("Arial", 20, "bold"), text_color=TEXT_ACCENT).pack(pady=(25, 10), anchor="w")

    transaction_frame = ctk.CTkFrame(dashboard_frame, fg_color=SECONDARY_DARK, corner_radius=10)
    transaction_frame.pack(fill="both", expand=True, pady=10)

    try:
        # Ensure transaction file exists before reading
        ensure_transaction_file() # Call again here just in case it was deleted somehow

        df = pd.read_csv("transactions.csv")
        # Filter for the current user and get the last 5 transactions
        user_df = df[df['username'] == current_user.uname.lower()].tail(5).copy() # Use lowercase and .copy()

        if not user_df.empty:
            # Create Header
            header_frame = ctk.CTkFrame(transaction_frame, fg_color="transparent")
            header_frame.pack(fill="x", padx=10, pady=(10, 5))
            ctk.CTkLabel(header_frame, text="Date", font=("Arial", 12, "bold"), width=150, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(header_frame, text="Type", font=("Arial", 12, "bold"), width=100, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(header_frame, text="Category/Details", font=("Arial", 12, "bold"), width=200, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(header_frame, text="Amount", font=("Arial", 12, "bold"), width=120, anchor="e").pack(side="right", padx=5)

            # Add transactions
            for index, row in user_df.iterrows():
                row_frame = ctk.CTkFrame(transaction_frame, fg_color="transparent")
                row_frame.pack(fill="x", padx=10, pady=2)
                # Handle potential errors in timestamp conversion
                try:
                    timestamp = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M')
                except Exception:
                    timestamp = "Invalid Date"

                ttype = row['type']
                category = row['category']
                # Handle potential errors in amount conversion
                try:
                     amount = float(row['amount'])
                except ValueError:
                     amount = 0.0 # Default to 0 if amount is invalid


                # Determine amount color based on transaction type
                inflow_types = ["Income", "Loan Received", "Transfer In"]
                amount_color = ACCENT_GREEN if ttype in inflow_types else ACCENT_RED

                ctk.CTkLabel(row_frame, text=timestamp, font=("Arial", 12), text_color=TEXT_LIGHT, width=150, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(row_frame, text=ttype, font=("Arial", 12), text_color=TEXT_LIGHT, width=100, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(row_frame, text=category, font=("Arial", 12), text_color=TEXT_LIGHT, width=200, anchor="w", justify="left", wraplength=190).pack(side="left", padx=5)
                ctk.CTkLabel(row_frame, text=format_currency(amount), font=("Arial", 12, "bold"), text_color=amount_color, width=120, anchor="e").pack(side="right", padx=5)
        else:
             ctk.CTkLabel(transaction_frame, text="No transactions recorded yet.", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=20)

    except FileNotFoundError:
        ctk.CTkLabel(transaction_frame, text="Transaction file not found.", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=20)
    except pd.errors.EmptyDataError:
         ctk.CTkLabel(transaction_frame, text="Transaction file is empty.", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=20)
    except Exception as e:
        ctk.CTkLabel(transaction_frame, text=f"Error loading transactions: {e}", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=20)
        print(f"Error reading transactions.csv in dashboard: {e}") # Debug print

# --- Income View ---
income_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Income"] = income_frame
income_amount_entry = None # Define globally for clearing

def update_income_view():
    global income_amount_entry
    if not current_user: return
    for widget in income_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(income_frame, text="Add Income", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")
    ctk.CTkLabel(income_frame, text="Enter the amount received:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(0,10), anchor="w")

    ctk.CTkLabel(income_frame, text="Amount:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w") # Added label
    income_amount_entry = ctk.CTkEntry(income_frame, placeholder_text="e.g., 5000.00", width=300, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    income_amount_entry.pack(pady=(0, 5), anchor="w") # Adjusted padding


    def handle_add_income():
        try:
            amount_str = income_amount_entry.get().strip()
            if not amount_str:
                 messagebox.showerror("Error", "Please enter an amount.")
                 return

            amount = float(amount_str)

            # amount validation is also done in logic.py, but a quick check here is fine
            if amount <= 0:
                 messagebox.showerror("Error", "Income amount must be positive.")
                 return

            # Call the logic method to add income to the user object and log the transaction
            msg = current_user.add_income(amount)

            if "✅" in msg:
                 # Save the updated state of all clients after a successful operation
                 save_all_clients(clients)
                 messagebox.showinfo("Income Added", msg)
                 income_amount_entry.delete(0, 'end') # Clear entry
                 update_dashboard_view() # Update dashboard after adding income
            else:
                 # Display error message returned from logic
                 messagebox.showerror("Error", msg)


        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for the amount.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            print(f"Error adding income: {e}") # Debug print


    ctk.CTkButton(income_frame, text="Add Income", command=handle_add_income, width=200, height=40, fg_color=ACCENT_GREEN, hover_color=ACCENT_BLUE, font=("Arial", 14, "bold"), corner_radius=10).pack(pady=20, anchor="w")

# --- Expense View ---
expense_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Expense"] = expense_frame
expense_amount_entry = None
expense_category_entry = None

def update_expense_view():
    global expense_amount_entry, expense_category_entry
    if not current_user: return
    for widget in expense_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(expense_frame, text="Record Expense", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")
    ctk.CTkLabel(expense_frame, text="Enter the amount spent and its category:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(0,10), anchor="w")

    ctk.CTkLabel(expense_frame, text="Amount:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w") # Added label
    expense_amount_entry = ctk.CTkEntry(expense_frame, placeholder_text="e.g., 350.50", width=300, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    expense_amount_entry.pack(pady=(0, 5), anchor="w") # Adjusted padding

    ctk.CTkLabel(expense_frame, text="Category:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w") # Added label
    expense_category_entry = ctk.CTkEntry(expense_frame, placeholder_text="e.g., Groceries, Bills", width=300, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    expense_category_entry.pack(pady=(0, 5), anchor="w") # Adjusted padding


    def handle_add_expense():
        try:
            amount_str = expense_amount_entry.get().strip()
            category = expense_category_entry.get().strip()

            if not amount_str:
                 messagebox.showerror("Error", "Please enter an amount.")
                 return
            if not category:
                messagebox.showerror("Error", "Please enter a category for the expense.")
                return

            amount = float(amount_str)

            # amount validation is also done in logic.py, but a quick check here is fine
            if amount <= 0:
                 messagebox.showerror("Error", "Expense amount must be positive.")
                 return

            # Call the logic method to record the expense
            msg = current_user.withdraw(amount, category)

            if "✅" in msg or "⚠️" in msg: # Success or Budget Alert
                 # Save the updated state of all clients after a successful/warned operation
                 save_all_clients(clients)
                 messagebox.showinfo("Expense Recorded", msg) # Use showinfo even for warning message
                 expense_amount_entry.delete(0, 'end')
                 expense_category_entry.delete(0, 'end')
                 update_dashboard_view() # Update dashboard
            else: # Handles "❌" messages from withdraw method
                messagebox.showerror("Error", msg)

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for the amount.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            print(f"Error adding expense: {e}") # Debug print


    ctk.CTkButton(expense_frame, text="Add Expense", command=handle_add_expense, width=200, height=40, fg_color=ACCENT_RED, hover_color=ACCENT_PINK, font=("Arial", 14, "bold"), corner_radius=10).pack(pady=20, anchor="w")


# --- Transfer View ---
transfer_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Transfer"] = transfer_frame
transfer_recipient_entry = None
transfer_amount_entry = None

def update_transfer_view():
    global transfer_recipient_entry, transfer_amount_entry
    if not current_user: return
    for widget in transfer_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(transfer_frame, text="Transfer Funds", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")
    ctk.CTkLabel(transfer_frame, text="Enter recipient username and amount:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(0,10), anchor="w")

    ctk.CTkLabel(transfer_frame, text="Recipient Username:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w") # Added label
    transfer_recipient_entry = ctk.CTkEntry(transfer_frame, placeholder_text="Username", width=300, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    transfer_recipient_entry.pack(pady=(0, 5), anchor="w") # Adjusted padding

    ctk.CTkLabel(transfer_frame, text="Amount:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w") # Added label
    transfer_amount_entry = ctk.CTkEntry(transfer_frame, placeholder_text="e.g., 100.00", width=300, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    transfer_amount_entry.pack(pady=(0, 5), anchor="w") # Adjusted padding


    def handle_transfer():
        # Check for child account restriction first
        if isinstance(current_user, ChildAccount):
             messagebox.showerror("Restriction", "Child accounts cannot initiate transfers.")
             return

        try:
            recipient_uname = transfer_recipient_entry.get().lower().strip()
            amount_str = transfer_amount_entry.get().strip()

            if not recipient_uname:
                messagebox.showerror("Error", "Please enter a recipient username.")
                return
            if not amount_str:
                 messagebox.showerror("Error", "Please enter an amount.")
                 return

            amount = float(amount_str)

            # amount validation is also done in logic.py, but a quick check here is fine
            if amount <= 0:
                messagebox.showerror("Error", "Transfer amount must be positive.")
                return
            if recipient_uname == current_user.uname.lower(): # Compare lowercase usernames
                messagebox.showerror("Error", "Cannot transfer funds to yourself.")
                return

            # Find recipient in the current clients list (already loaded in memory)
            receiver = find_client_by_username(clients, recipient_uname)

            if receiver:
                # Call the logic method to perform the transfer on user objects and log transactions
                msg = current_user.transfer(receiver, amount)

                if "✅" in msg:
                    # Save the updated state of *all* clients after a successful transfer
                    save_all_clients(clients)
                    messagebox.showinfo("Transfer Success", msg)
                    transfer_recipient_entry.delete(0, 'end')
                    transfer_amount_entry.delete(0, 'end')
                    update_dashboard_view() # Update dashboard (balance changes)
                else: # Handles "❌" messages from transfer method
                    messagebox.showerror("Transfer Failed", msg)
            else:
                messagebox.showerror("Error", f"Recipient user '{recipient_uname}' not found.")

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for the amount.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            print(f"Error handling transfer: {e}") # Debug print


    ctk.CTkButton(transfer_frame, text="Send Money", command=handle_transfer, width=200, height=40, fg_color=ACCENT_PINK, hover_color=ACCENT_PURPLE, font=("Arial", 14, "bold"), corner_radius=10).pack(pady=20, anchor="w")


# --- Loans View ---
loans_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Loans"] = loans_frame
loan_request_entry = None
loan_repay_entry = None
loan_status_label = None

def update_loans_view():
    global loan_request_entry, loan_repay_entry, loan_status_label
    if not current_user: return
    for widget in loans_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(loans_frame, text="Loan Management", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")

    # Display Current Loan Status
    # Use current_user.loans directly as display_balance is for account balance
    loan_status_label = ctk.CTkLabel(loans_frame, text=f"Current Outstanding Loan: {format_currency(current_user.loans)}", font=("Arial", 16), text_color=TEXT_LIGHT)
    loan_status_label.pack(pady=(0,20), anchor="w")

    # --- Request Loan Section ---
    req_frame = ctk.CTkFrame(loans_frame, fg_color="transparent")
    req_frame.pack(fill="x", pady=10)
    ctk.CTkLabel(req_frame, text="Request a New Loan", font=("Arial", 16, "bold"), text_color=ACCENT_BLUE).pack(anchor="w")

    ctk.CTkLabel(req_frame, text="Amount to Request:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w", side="top") # Added label
    loan_request_entry = ctk.CTkEntry(req_frame, placeholder_text="Amount", width=250, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    loan_request_entry.pack(pady=5, side="left", padx=(0, 10)) # Adjusted padding


    def handle_request_loan():
        # Check for child account restriction
        if isinstance(current_user, ChildAccount):
            messagebox.showerror("Restriction", "Child accounts are not eligible for loans.")
            return
        try:
            amount_str = loan_request_entry.get().strip()
            if not amount_str:
                 messagebox.showerror("Error", "Please enter an amount.")
                 return

            amount = float(amount_str)

            # amount validation also in logic.py, but a quick check here is fine
            if amount <= 0:
                messagebox.showerror("Error", "Loan amount must be positive.")
                return

            # Call the logic method to request the loan
            msg = current_user.request_loan(amount)

            if "✅" in msg:
                # Save the updated state after successful operation
                save_all_clients(clients)
                messagebox.showinfo("Loan Request", msg)
                loan_request_entry.delete(0, 'end')
                # Update the loan status label directly
                loan_status_label.configure(text=f"Current Outstanding Loan: {format_currency(current_user.loans)}")
                update_dashboard_view() # Update balance on dashboard
            else: # Handles "❌" messages from request_loan method
                messagebox.showerror("Loan Request Failed", msg)

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid loan amount.")
        except Exception as e:
             messagebox.showerror("Error", f"An error occurred: {e}")
             print(f"Error handling loan request: {e}") # Debug print


    ctk.CTkButton(req_frame, text="Request Loan", command=handle_request_loan, width=150, height=35, fg_color=ACCENT_BLUE, hover_color=ACCENT_GREEN, font=("Arial", 14, "bold"), corner_radius=10).pack(side="left")


    # --- Repay Loan Section ---
    repay_frame = ctk.CTkFrame(loans_frame, fg_color="transparent")
    repay_frame.pack(fill="x", pady=10,padx=0) # Corrected _padx to padx
    ctk.CTkLabel(repay_frame, text="Repay Loan", font=("Arial", 16, "bold"), text_color=ACCENT_GREEN).pack(anchor="w")

    ctk.CTkLabel(repay_frame, text="Amount to Repay:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w", side="top") # Added label
    loan_repay_entry = ctk.CTkEntry(repay_frame, placeholder_text="Amount", width=250, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    loan_repay_entry.pack(pady=5, side="left", padx=(0, 10)) # Adjusted padding


    def handle_repay_loan():
        try:
            amount_str = loan_repay_entry.get().strip()
            if not amount_str:
                 messagebox.showerror("Error", "Please enter an amount.")
                 return

            amount = float(amount_str)

            # amount validation also in logic.py, but a quick check here is fine
            if amount <= 0:
                 messagebox.showerror("Error", "Repayment amount must be positive.")
                 return
            if amount > current_user.amount:
                messagebox.showerror("Error", "Cannot repay. Insufficient funds.")
                return
            if amount > current_user.loans:
                # Allow repaying less than the outstanding loan, but not more
                messagebox.showerror("Error", f"Cannot repay more than the outstanding loan amount ({current_user.loans:.2f}).")
                return


            # Call the logic method to repay the loan
            msg = current_user.repay_loan(amount)

            if "✅" in msg:
                # Save the updated state after successful operation
                save_all_clients(clients)
                messagebox.showinfo("Loan Repayment", msg)
                loan_repay_entry.delete(0, 'end')
                # Update the loan status label directly
                loan_status_label.configure(text=f"Current Outstanding Loan: {format_currency(current_user.loans)}")
                update_dashboard_view() # Update balance on dashboard
            else: # Handles "❌" messages from repay_loan method
                messagebox.showerror("Repayment Failed", msg)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid repayment amount.")
        except Exception as e:
             messagebox.showerror("Error", f"An error occurred: {e}")
             print(f"Error handling loan repayment: {e}") # Debug print


    ctk.CTkButton(repay_frame, text="Repay Loan", command=handle_repay_loan, width=150, height=35, fg_color=ACCENT_GREEN, hover_color=ACCENT_BLUE, font=("Arial", 14, "bold"), corner_radius=10).pack(side="left")


# --- Budget View ---
budget_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Budget"] = budget_frame
budget_entry = None
budget_status_label = None
budget_remaining_label = None
budget_prog_bar = None # Define globally to update easily

def update_budget_view():
    global budget_entry, budget_status_label, budget_remaining_label, budget_prog_bar
    if not current_user: return
    for widget in budget_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(budget_frame, text="Manage Budget", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")

    # Display Current Budget Status
    current_budget = current_user.display_budget() # Get current budget value
    # Ensure total_spent is a number before calculation
    total_spent_val = current_user.total_spent if isinstance(current_user.total_spent, (int, float)) else 0

    budget_status_label = ctk.CTkLabel(budget_frame, text=f"Current Monthly Budget: {format_currency(current_budget)}", font=("Arial", 16), text_color=TEXT_LIGHT)
    budget_status_label.pack(pady=(0,5), anchor="w")

    remaining_str = "N/A"
    progress = 0.0 # Represents the portion of budget *spent*
    if current_budget > 0:
        remaining = current_budget - total_spent_val
        remaining_str = format_currency(remaining)
         # Progress is total_spent divided by budget, capped between 0 and 1
        progress = max(0.0, min(1.0, (total_spent_val / current_budget)))
    else:
        remaining_str = "No Budget Set"
        progress = 0.0 # No budget means 0% progress towards it

    budget_remaining_label = ctk.CTkLabel(budget_frame, text=f"Remaining This Month: {remaining_str}", font=("Arial", 16), text_color=ACCENT_BLUE)
    budget_remaining_label.pack(pady=(0,20), anchor="w")

    # Progress bar and percentage display for budget
    budget_prog_bar = ctk.CTkProgressBar(budget_frame, orientation="horizontal", progress_color=PROGRESS_BAR, fg_color=ENTRY_FIELD)
    budget_prog_bar.set(progress) # Set bar value based on spent proportion

    # Label to show percentage usage next to the bar
    ctk.CTkLabel(budget_frame, text=f"{progress:.1%} Used", font=("Arial", 12), text_color=TEXT_LIGHT).pack(pady=(0, 2), padx=20, anchor="w")
    budget_prog_bar.pack(pady=(0, 10), padx=20, fill="x")


    # Set/Update Budget Section
    ctk.CTkLabel(budget_frame, text="Set New Monthly Budget", font=("Arial", 16, "bold"), text_color=ACCENT_PINK).pack(anchor="w", pady=(10,5))

    ctk.CTkLabel(budget_frame, text="Amount:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(5, 0), padx=0, anchor="w") # Added label
    budget_entry = ctk.CTkEntry(budget_frame, placeholder_text="e.g., 20000.00", width=300, height=35, corner_radius=10, fg_color=ENTRY_FIELD)
    budget_entry.pack(pady=(0, 5), anchor="w") # Adjusted padding


    def handle_set_budget():
        try:
            new_budget_str = budget_entry.get().strip()
            if not new_budget_str:
                 messagebox.showerror("Error", "Please enter a budget amount.")
                 return

            new_budget = float(new_budget_str)

            # Validation also in logic, but quick check here
            if new_budget < 0:
                messagebox.showerror("Error", "Budget cannot be negative.")
                return

            # Call the logic method to set the budget
            msg = current_user.set_budget(new_budget)

            if "✅" in msg:
                # Save the updated state after successful operation
                save_all_clients(clients)
                messagebox.showinfo("Budget Updated", msg) # Show message from logic
                budget_entry.delete(0, 'end')
                # Update labels and progress bar directly after setting budget and saving
                updated_budget = current_user.display_budget()
                updated_total_spent = current_user.total_spent if isinstance(current_user.total_spent, (int, float)) else 0

                budget_status_label.configure(text=f"Current Monthly Budget: {format_currency(updated_budget)}")

                updated_remaining_str = "N/A"
                updated_progress = 0.0
                if updated_budget > 0:
                    updated_remaining = updated_budget - updated_total_spent
                    updated_remaining_str = format_currency(updated_remaining)
                    updated_progress = max(0.0, min(1.0, (updated_total_spent / updated_budget)))
                else:
                    updated_remaining_str = "No Budget Set"
                    updated_progress = 0.0

                budget_remaining_label.configure(text=f"Remaining This Month: {updated_remaining_str}")
                budget_prog_bar.set(updated_progress) # Update progress bar
                 # Update percentage label (assuming it's the next widget after the progress bar's parent frame)
                # A more robust way might be to store the label in a global variable too
                # For now, rely on widget packing order: label is likely the 4th child of the budget_frame if packed sequentially
                # Find the label containing the percentage text
                for child in budget_frame.winfo_children():
                     if isinstance(child, ctk.CTkLabel) and "Used" in child.cget("text"):
                         child.configure(text=f"{updated_progress:.1%} Used")
                         break


                update_dashboard_view() # Update dashboard as well (budget section there)

            else: # Handles "❌" messages from set_budget method
                messagebox.showerror("Budget Update Failed", msg)


        except ValueError:
            messagebox.showerror("Error", "Please enter a valid budget amount.")
        except Exception as e:
             messagebox.showerror("Error", f"An error occurred: {e}")
             print(f"Error setting budget: {e}") # Debug print


    ctk.CTkButton(budget_frame, text="Set Budget", command=handle_set_budget, width=200, height=40, fg_color=ACCENT_PINK, hover_color=ACCENT_PURPLE, font=("Arial", 14, "bold"), corner_radius=10).pack(pady=20, anchor="w")


# --- Graphs View ---
graphs_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Graphs"] = graphs_frame
# Keep image labels global to prevent garbage collection issues
monthly_img_label = None
pie_img_label = None

def update_graphs_view():
    global monthly_img_label, pie_img_label
    if not current_user: return
    for widget in graphs_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(graphs_frame, text="Financial Graphs", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")

    # Generate charts using logic function which saves them as files
    try:
        # plot_charts function saves the images to filenames based on username
        plot_charts(current_user.uname)
        monthly_path = f"{current_user.uname.lower()}_monthly_trend.png" # Ensure lowercase for filename consistency
        pie_path = f"{current_user.uname.lower()}_expense_pie.png"     # Ensure lowercase for filename consistency

        # --- Display Monthly Trend ---
        ctk.CTkLabel(graphs_frame, text="Monthly Net Cash Flow", font=("Arial", 16, "bold"), text_color=TEXT_LIGHT).pack(pady=(10,5), anchor="w")
        if os.path.exists(monthly_path):
            try:
                # Open the image file using PIL
                monthly_pil_image = Image.open(monthly_path)
                # Resize if necessary to fit in the GUI without being too large
                max_width = 800 # Maximum width for the chart image in GUI
                # Calculate aspect ratio to maintain proportions, but don't enlarge
                ratio = min(max_width / monthly_pil_image.width, 1.0) # Cap ratio at 1.0
                new_size = (int(monthly_pil_image.width * ratio), int(monthly_pil_image.height * ratio))
                # Resize the image using a high-quality filter
                monthly_pil_image = monthly_pil_image.resize(new_size, Image.Resampling.BICUBIC) # Use Image.Resampling

                # Convert the PIL image to a CustomTkinter compatible image
                monthly_ctk_image = ImageTk.PhotoImage(monthly_pil_image)

                # Create or update the label that displays the image
                if monthly_img_label is None or not monthly_img_label.winfo_exists(): # Check if label exists or was destroyed
                     monthly_img_label = ctk.CTkLabel(graphs_frame, text="", image=monthly_ctk_image)
                else:
                    monthly_img_label.configure(image=monthly_ctk_image)
                # Keep a reference to the CTkImage object to prevent it from being garbage collected
                monthly_img_label.image = monthly_ctk_image
                monthly_img_label.pack(pady=5)

            except FileNotFoundError: # Should be caught by the outer try, but included for safety
                 ctk.CTkLabel(graphs_frame, text="Monthly trend chart file not found after generation attempt.", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=5)
            except Exception as img_e:
                ctk.CTkLabel(graphs_frame, text=f"Error displaying monthly chart: {img_e}", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=5)
                print(f"Error displaying monthly chart: {img_e}") # Debug print
        else:
             # Display a message if the chart file does not exist (e.g., not enough data)
             ctk.CTkLabel(graphs_frame, text="Monthly trend chart not available (not enough data or generation error).", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=5)


        # --- Display Expense Pie Chart ---
        ctk.CTkLabel(graphs_frame, text="Expense Breakdown", font=("Arial", 16, "bold"), text_color=TEXT_LIGHT).pack(pady=(20,5), anchor="w")
        if os.path.exists(pie_path):
            try:
                # Open the image file using PIL
                pie_pil_image = Image.open(pie_path)
                # Resize if necessary
                max_width_pie = 500 # Maximum width for the pie chart image
                ratio_pie = min(max_width_pie / pie_pil_image.width, 1.0) # Cap ratio at 1.0
                new_size_pie = (int(pie_pil_image.width * ratio_pie), int(pie_pil_image.height * ratio_pie))
                 # Resize the image using a high-quality filter
                pie_pil_image = pie_pil_image.resize(new_size_pie, Image.Resampling.BICUBIC) # Use Image.Resampling

                # Convert the PIL image to a CustomTkinter compatible image
                pie_ctk_image = ImageTk.PhotoImage(pie_pil_image)

                # Create or update the label that displays the image
                if pie_img_label is None or not pie_img_label.winfo_exists(): # Check if label exists or was destroyed
                    pie_img_label = ctk.CTkLabel(graphs_frame, text="", image=pie_ctk_image)
                else:
                     pie_img_label.configure(image=pie_ctk_image)
                # Keep a reference to the CTkImage object
                pie_img_label.image = pie_ctk_image
                pie_img_label.pack(pady=5)

            except FileNotFoundError: # Should be caught by outer try, but included for safety
                 ctk.CTkLabel(graphs_frame, text="Expense pie chart file not found after generation attempt.", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=5)
            except Exception as img_e:
                ctk.CTkLabel(graphs_frame, text=f"Error displaying pie chart: {img_e}", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=5)
                print(f"Error displaying pie chart: {img_e}") # Debug print
        else:
            # Display a message if the chart file does not exist
            ctk.CTkLabel(graphs_frame, text="Expense pie chart not available (not enough data or generation error).", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=5)

    except FileNotFoundError:
         ctk.CTkLabel(graphs_frame, text="Transaction data file not found to generate graphs.", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=20)
         print("transactions.csv not found in update_graphs_view.") # Debug print
    except pd.errors.EmptyDataError:
         ctk.CTkLabel(graphs_frame, text="Transaction data file is empty, cannot generate graphs.", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=20)
         print("transactions.csv is empty in update_graphs_view.") # Debug print
    except Exception as e:
        # Catch the specific pandas parser error and provide a more tailored message
        if "Error tokenizing data" in str(e) and "saw" in str(e):
             error_message = f"Error reading transaction data: Inconsistent format found in transactions.csv (e.g., extra commas). Please check or delete the transactions.csv file. Details: {e}"
        else:
             error_message = f"Could not generate or display graphs: {e}"

        messagebox.showerror("Graph Error", error_message)
        ctk.CTkLabel(graphs_frame, text=f"Error generating graphs: {error_message}", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=20)
        print(f"Graph generation error in update_graphs_view: {e}") # Debug print


# --- AI Overview View ---
ai_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["AI Overview"] = ai_frame
# ai_prediction_label = None # Keep label global to update its text - Replaced by graph label
# Global variable to hold the prediction image reference
prediction_img_label = None


def update_ai_overview_view():
    global prediction_img_label # Use the global variable
    if not current_user: return
    for widget in ai_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(ai_frame, text="AI Expense Prediction", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")

    # --- Display Next Month's Predicted Amount ---
    # Call the new function to get the next month's prediction message
    next_month_prediction_message = predict_next_month_expense(current_user.uname)
    # Determine text color based on message content
    msg_color = ACCENT_GREEN if "📈" in next_month_prediction_message and "Error" not in next_month_prediction_message else ACCENT_RED


    ctk.CTkLabel(ai_frame, text=next_month_prediction_message, font=("Arial", 16), text_color=msg_color).pack(pady=(0,20), anchor="w")


    # --- Display Historical and Predicted Cumulative Expense Graph ---
    ctk.CTkLabel(ai_frame, text="Historical and Predicted Cumulative Expense Trend:", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(0,10), anchor="w")

    # Call the logic function to generate data and save the plot
    prediction_result = predict_future_expense_data(current_user.uname)
    plot_path = prediction_result.get("plot_path")
    message = prediction_result.get("message", "An unknown error occurred.") # Message related to graph generation

    if plot_path and os.path.exists(plot_path):
        try:
            # Open the image file using PIL
            prediction_pil_image = Image.open(plot_path)
            # Resize if necessary
            max_width = 800 # Maximum width for the plot image
            ratio = min(max_width / prediction_pil_image.width, 1.0)
            new_size = (int(prediction_pil_image.width * ratio), int(prediction_pil_image.height * ratio))
            prediction_pil_image = prediction_pil_image.resize(new_size, Image.Resampling.BICUBIC)

            # Convert to CustomTkinter compatible image
            prediction_ctk_image = ImageTk.PhotoImage(prediction_pil_image)

            # Create or update the label
            if prediction_img_label is None or not prediction_img_label.winfo_exists():
                 prediction_img_label = ctk.CTkLabel(ai_frame, text="", image=prediction_ctk_image)
            else:
                 prediction_img_label.configure(image=prediction_ctk_image)

            # Keep a reference
            prediction_img_label.image = prediction_ctk_image
            prediction_img_label.pack(pady=20)

            # Display graph generation message below the graph (if any, e.g., success/error)
            # We already displayed the next month prediction message above
            # ctk.CTkLabel(ai_frame, text=message, font=("Arial", 12), text_color=TEXT_LIGHT).pack(pady=(0,10)) # Optional: if you want a second message specific to graph

        except FileNotFoundError: # Should be caught by logic, but safety
             ctk.CTkLabel(ai_frame, text="Prediction chart file not found after generation attempt.", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=20)
        except Exception as img_e:
            ctk.CTkLabel(ai_frame, text=f"Error displaying prediction chart: {img_e}", font=("Arial", 14), text_color=ACCENT_RED).pack(pady=20)
            print(f"Error displaying prediction chart: {img_e}") # Debug print

    else:
        # Display graph generation error message if plot was not created
        ctk.CTkLabel(ai_frame, text=message, font=("Arial", 14), text_color=ACCENT_RED).pack(pady=20)


# --- Export Data View ---
export_frame = ctk.CTkFrame(main_content, fg_color=PRIMARY_DARK)
content_frames["Export Data"] = export_frame

def update_export_data_view():
    if not current_user: return
    for widget in export_frame.winfo_children(): widget.destroy() # Clear previous content

    ctk.CTkLabel(export_frame, text="Export Transaction Data", font=("Arial", 24, "bold"), text_color=TEXT_ACCENT).pack(pady=20, anchor="w")
    ctk.CTkLabel(export_frame, text="Export all your transaction history to a CSV file.", font=("Arial", 14), text_color=TEXT_LIGHT).pack(pady=(0,10), anchor="w")

    def handle_export_data():
        try:
            # Call the logic function to export data
            export_msg = export_user_data(current_user.uname)
            if "✅" in export_msg:
                 messagebox.showinfo("Export Success", export_msg)
            else: # Handles messages indicating no data or other errors from logic.py
                 messagebox.showerror("Export Failed", export_msg)

        except FileNotFoundError:
             # This might be caught by logic.py and return a message, but included here for safety
             messagebox.showerror("Export Error", "Transaction data file not found to export.")
             print("transactions.csv not found in handle_export_data.") # Debug print
        except pd.errors.EmptyDataError:
             messagebox.showerror("Export Error", "No transaction data found to export (file is empty).")
             print("transactions.csv is empty in handle_export_data.") # Debug print
        except Exception as e:
             # Catch the specific pandas parser error and provide a more tailored message
             if "Error tokenizing data" in str(e) and "saw" in str(e):
                 error_message = f"Error reading transaction data for export: Inconsistent format found in transactions.csv (e.g., extra commas). Please check or delete the transactions.csv file. Details: {e}"
             else:
                 error_message = f"Could not export data: {e}"

             messagebox.showerror("Export Error", error_message)
             print(f"Error exporting data: {e}") # Debug print


    ctk.CTkButton(export_frame, text="Export My Data", command=handle_export_data, width=200, height=40, fg_color=ACCENT_BLUE, hover_color=ACCENT_GREEN, font=("Arial", 14, "bold"), corner_radius=10).pack(pady=20, anchor="w")


# --- ==================== App Initialization ==================== ---

def handle_logout():
    """Logs the current user out and returns to the login screen."""
    global current_user
    if current_user:
         # Save the current user's state before logging out
         save_all_clients(clients)
         print(f"Logging out user: {current_user.uname}")
    current_user = None

    # Hide main content and sidebar
    # switch_view("Login") handles hiding other frames and showing the login view
    switch_view("Login")

    # Hide sidebar
    sidebar.pack_forget()

    # Ensure login fields are cleared on logout
    if login_user_entry: login_user_entry.delete(0, 'end')
    if login_pass_entry: login_pass_entry.delete(0, 'end')

    messagebox.showinfo("Logout", "You have been successfully logged out.")


# --- Initial Setup ---
ensure_transaction_file() # Make sure transactions CSV exists with headers
load_initial_users()    # Load users initially using the new function from logic.py

# Start the application at the login screen
switch_view("Login")      # This will show the auth_frame and the login_sub_frame within it

# Assign update functions to app object (for easy calling in switch_view)
# This mechanism is correct for calling the specific view update functions
app.update_dashboard_view = update_dashboard_view
app.update_income_view = update_income_view
app.update_expense_view = update_expense_view
app.update_transfer_view = update_transfer_view
app.update_loans_view = update_loans_view
app.update_budget_view = update_budget_view
app.update_graphs_view = update_graphs_view
app.update_ai_overview_view = update_ai_overview_view
app.update_export_data_view = update_export_data_view
# No specific update needed for login/register frames usually

app.mainloop()