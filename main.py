import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

# 1. DATABASE CONNECTION AND TABLE CREATION

conn = sqlite3.connect("library.db")

# Enable foreign-key checking for this connection.
conn.execute("PRAGMA foreign_keys = ON")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    book_id TEXT PRIMARY KEY COLLATE NOCASE,
    title TEXT NOT NULL,
    author TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT NOT NULL,
    student_name TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    return_date TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
)
""")

# A book can have only one active issue record at a time.
cursor.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS one_active_issue
ON issues(book_id)
WHERE return_date IS NULL
""")

conn.commit()

# 2. MAIN WINDOW

root = tk.Tk()
root.title("Library Management System")
root.geometry("1100x720")
root.minsize(900, 620)
root.configure(bg="#F2F5F9")

# 3. DATABASE FUNCTIONS

def get_books(search="", status="All"):
    """Fetch books and calculate their current availability."""

    query = """
    SELECT
        b.book_id,
        b.title,
        b.author,
        CASE
            WHEN i.issue_id IS NULL THEN 'Available'
            ELSE 'Issued'
        END AS book_status,
        COALESCE(i.student_name, '-'),
        COALESCE(i.issue_date, '-')
    FROM books AS b
    LEFT JOIN issues AS i
        ON b.book_id = i.book_id
        AND i.return_date IS NULL
    WHERE (b.title LIKE ? OR b.author LIKE ?)
    """
    params = [f"%{search}%", f"%{search}%"]

    if status != "All":
        query += """
        AND (
            CASE
                WHEN i.issue_id IS NULL THEN 'Available'
                ELSE 'Issued'
            END
        ) = ?
        """
        params.append(status)

    query += " ORDER BY b.title COLLATE NOCASE"

    cursor.execute(query, params)
    return cursor.fetchall()

# 4. DASHBOARD STATISTICS

def update_dashboard():
    cursor.execute("SELECT COUNT(*) FROM books")
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM issues
        WHERE return_date IS NULL
    """)
    issued = cursor.fetchone()[0]

    available = total - issued

    total_label.config(text=str(total))
    available_label.config(text=str(available))
    issued_label.config(text=str(issued))

# 5. DISPLAY / REFRESH BOOKS

def refresh_books():
    for item in book_table.get_children():
        book_table.delete(item)

    books = get_books(search_var.get(), status_var.get())

    for book in books:
        book_table.insert("", tk.END, values=book)

    update_dashboard()

# 6. ADD NEW BOOK

def add_book():
    book_id = id_entry.get().strip().upper()
    title = title_entry.get().strip()
    author = author_entry.get().strip()

    if not book_id or not title or not author:
        messagebox.showwarning(
            "Missing Information",
            "Please enter Book ID, Title and Author."
        )
        return

    try:
        # Extra case-insensitive duplicate check.
        cursor.execute(
            "SELECT 1 FROM books WHERE book_id = ? COLLATE NOCASE",
            (book_id,)
        )

        if cursor.fetchone():
            messagebox.showerror(
                "Duplicate Book ID",
                "This Book ID already exists."
            )
            return

        cursor.execute("""
            INSERT INTO books (book_id, title, author)
            VALUES (?, ?, ?)
        """, (book_id, title, author))

        conn.commit()

        messagebox.showinfo("Success", "Book added successfully!")

        id_entry.delete(0, tk.END)
        title_entry.delete(0, tk.END)
        author_entry.delete(0, tk.END)

        refresh_books()

    except sqlite3.IntegrityError:
        conn.rollback()
        messagebox.showerror(
            "Database Error",
            "The Book ID already exists or the data violates a database rule."
        )

    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Database Error", str(e))

# 7. ISSUE BOOK

def issue_book():
    selected = book_table.selection()

    if not selected:
        messagebox.showwarning(
            "Selection Required",
            "Please select a book first."
        )
        return

    book = book_table.item(selected[0], "values")
    book_id = book[0]

    student_name = student_entry.get().strip()

    if not student_name:
        messagebox.showwarning(
            "Missing Information",
            "Please enter the student's name."
        )
        return

    try:
        # Check the database directly instead of relying only
        # on the status currently displayed in the table.
        cursor.execute("""
            SELECT 1
            FROM issues
            WHERE book_id = ?
            AND return_date IS NULL
        """, (book_id,))

        if cursor.fetchone():
            messagebox.showerror(
                "Book Unavailable",
                "This book is already issued."
            )
            refresh_books()
            return

        issue_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO issues
            (book_id, student_name, issue_date)
            VALUES (?, ?, ?)
        """, (book_id, student_name, issue_date))

        conn.commit()

        messagebox.showinfo(
            "Success",
            f"Book issued successfully to {student_name}!"
        )

        student_entry.delete(0, tk.END)
        refresh_books()

    except sqlite3.IntegrityError:
        conn.rollback()
        messagebox.showerror(
            "Issue Failed",
            "This book is already issued or the selected record is invalid."
        )
        refresh_books()

    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Database Error", str(e))

# 8. RETURN BOOK

def return_book():
    selected = book_table.selection()

    if not selected:
        messagebox.showwarning(
            "Selection Required",
            "Please select a book first."
        )
        return

    book = book_table.item(selected[0], "values")
    book_id = book[0]

    try:
        # Check the current database status.
        cursor.execute("""
            SELECT issue_id
            FROM issues
            WHERE book_id = ?
            AND return_date IS NULL
        """, (book_id,))

        active_issue = cursor.fetchone()

        if active_issue is None:
            messagebox.showerror(
                "Invalid Return",
                "This book is not currently issued."
            )
            refresh_books()
            return

        return_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE issues
            SET return_date = ?
            WHERE issue_id = ?
            AND return_date IS NULL
        """, (return_date, active_issue[0]))

        if cursor.rowcount == 0:
            conn.rollback()
            messagebox.showerror(
                "Return Failed",
                "The active issue record could not be updated."
            )
            refresh_books()
            return

        conn.commit()

        messagebox.showinfo("Success", "Book returned successfully!")
        refresh_books()

    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Database Error", str(e))

# 9. DELETE BOOK

def delete_book():
    selected = book_table.selection()

    if not selected:
        messagebox.showwarning(
            "Selection Required",
            "Please select a book to delete."
        )
        return

    book = book_table.item(selected[0], "values")
    book_id = book[0]
    book_title = book[1]

    try:
        # Preserve the issue history: delete only books
        # that have never been issued.
        cursor.execute(
            "SELECT 1 FROM issues WHERE book_id = ? LIMIT 1",
            (book_id,)
        )

        if cursor.fetchone():
            messagebox.showerror(
                "Cannot Delete Book",
                "This book has issue history. It cannot be deleted "
                "so that library records remain preserved."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete '{book_title}'?"
        )

        if not confirm:
            return

        cursor.execute(
            "DELETE FROM books WHERE book_id = ?",
            (book_id,)
        )
        conn.commit()

        messagebox.showinfo("Success", "Book deleted successfully!")
        refresh_books()

    except sqlite3.IntegrityError:
        conn.rollback()
        messagebox.showerror(
            "Delete Failed",
            "This book is linked to another database record."
        )

    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Database Error", str(e))

# 10. ISSUE HISTORY WINDOW

def show_issue_history():
    history_window = tk.Toplevel(root)
    history_window.title("Book Issue History")
    history_window.geometry("950x450")
    history_window.configure(bg="#F2F5F9")

    tk.Label(
        history_window,
        text="BOOK ISSUE HISTORY",
        font=("Arial", 16, "bold"),
        bg="#F2F5F9",
        fg="#183153"
    ).pack(pady=15)

    history_frame = tk.Frame(history_window, bg="white")
    history_frame.pack(fill="both", expand=True, padx=15, pady=10)

    history_columns = (
        "Issue ID",
        "Book ID",
        "Title",
        "Student",
        "Issue Date",
        "Return Date",
        "Status"
    )

    history_table = ttk.Treeview(
        history_frame,
        columns=history_columns,
        show="headings"
    )

    history_widths = [75, 85, 175, 130, 155, 155, 95]

    for column, width in zip(history_columns, history_widths):
        history_table.heading(column, text=column)
        history_table.column(column, width=width, anchor="center")

    scrollbar = ttk.Scrollbar(
        history_frame,
        orient="vertical",
        command=history_table.yview
    )

    history_table.configure(yscrollcommand=scrollbar.set)
    history_table.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    try:
        cursor.execute("""
            SELECT
                i.issue_id,
                b.book_id,
                b.title,
                i.student_name,
                i.issue_date,
                COALESCE(i.return_date, '-'),
                CASE
                    WHEN i.return_date IS NULL THEN 'Issued'
                    ELSE 'Returned'
                END
            FROM issues AS i
            JOIN books AS b ON i.book_id = b.book_id
            ORDER BY i.issue_id DESC
        """)

        records = cursor.fetchall()

        for record in records:
            history_table.insert("", tk.END, values=record)

        if not records:
            messagebox.showinfo(
                "No History",
                "No book issue records are available yet.",
                parent=history_window
            )

    except sqlite3.Error as e:
        messagebox.showerror(
            "Database Error",
            str(e),
            parent=history_window
        )

# 11. SEARCH BOOKS

def search_books(*args):
    refresh_books()

# 12. GUI DESIGN

# Main heading

header = tk.Frame(root, bg="#183153", height=75)
header.pack(fill="x")

tk.Label(
    header,
    text="LIBRARY MANAGEMENT SYSTEM",
    font=("Arial", 20, "bold"),
    bg="#183153",
    fg="white"
).pack(pady=20)

# Dashboard

dashboard = tk.Frame(root, bg="#F2F5F9")
dashboard.pack(fill="x", padx=20, pady=15)

def create_card(parent, title, color):
    card = tk.Frame(
        parent,
        bg="white",
        highlightbackground="#DCE3EC",
        highlightthickness=1
    )

    card.pack(side="left", expand=True, fill="both", padx=7)

    tk.Label(
        card,
        text=title,
        font=("Arial", 11, "bold"),
        bg="white",
        fg="#526176"
    ).pack(pady=(12, 3))

    label = tk.Label(
        card,
        text="0",
        font=("Arial", 23, "bold"),
        bg="white",
        fg=color
    )
    label.pack(pady=(0, 12))

    return label

total_label = create_card(dashboard, "TOTAL BOOKS", "#183153")
available_label = create_card(dashboard, "AVAILABLE", "#16834A")
issued_label = create_card(dashboard, "ISSUED", "#D97706")

# Main content frame

content = tk.Frame(root, bg="#F2F5F9")
content.pack(fill="both", expand=True, padx=20, pady=5)

# Add book section

add_frame = tk.LabelFrame(
    content,
    text=" Add New Book ",
    font=("Arial", 11, "bold"),
    bg="white",
    padx=12,
    pady=10
)
add_frame.pack(fill="x", pady=5)

tk.Label(add_frame, text="Book ID", bg="white").grid(
    row=0, column=0, padx=5, pady=5
)

id_entry = ttk.Entry(add_frame, width=18)
id_entry.grid(row=0, column=1, padx=5)

tk.Label(add_frame, text="Title", bg="white").grid(
    row=0, column=2, padx=5
)

title_entry = ttk.Entry(add_frame, width=23)
title_entry.grid(row=0, column=3, padx=5)

tk.Label(add_frame, text="Author", bg="white").grid(
    row=0, column=4, padx=5
)

author_entry = ttk.Entry(add_frame, width=18)
author_entry.grid(row=0, column=5, padx=5)

ttk.Button(
    add_frame,
    text="Add Book",
    command=add_book
).grid(row=0, column=6, padx=8)

# Search and filter section

filter_frame = tk.Frame(content, bg="#F2F5F9")
filter_frame.pack(fill="x", pady=10)

tk.Label(
    filter_frame,
    text="Search:",
    font=("Arial", 10, "bold"),
    bg="#F2F5F9"
).pack(side="left", padx=5)

search_var = tk.StringVar()
search_var.trace_add("write", search_books)

search_entry = ttk.Entry(
    filter_frame,
    textvariable=search_var,
    width=30
)
search_entry.pack(side="left", padx=5)

tk.Label(
    filter_frame,
    text="Filter:",
    bg="#F2F5F9"
).pack(side="left", padx=(15, 5))

status_var = tk.StringVar(value="All")

status_combo = ttk.Combobox(
    filter_frame,
    textvariable=status_var,
    values=["All", "Available", "Issued"],
    state="readonly",
    width=13
)
status_combo.pack(side="left")
status_combo.bind("<<ComboboxSelected>>", search_books)

ttk.Button(
    filter_frame,
    text="Refresh",
    command=refresh_books
).pack(side="right", padx=5)

ttk.Button(
    filter_frame,
    text="Issue History",
    command=show_issue_history
).pack(side="right", padx=5)

# Book table

table_frame = tk.Frame(content, bg="white")
table_frame.pack(fill="both", expand=True, pady=5)

columns = (
    "ID",
    "Title",
    "Author",
    "Status",
    "Student",
    "Issue Date"
)

book_table = ttk.Treeview(
    table_frame,
    columns=columns,
    show="headings",
    height=10
)

widths = [80, 200, 155, 100, 155, 150]

for column, width in zip(columns, widths):
    book_table.heading(column, text=column)
    book_table.column(column, width=width, anchor="center")

book_table.pack(side="left", fill="both", expand=True)

scrollbar = ttk.Scrollbar(
    table_frame,
    orient="vertical",
    command=book_table.yview
)

scrollbar.pack(side="right", fill="y")
book_table.configure(yscrollcommand=scrollbar.set)

# Issue, return and delete section

action_frame = tk.LabelFrame(
    content,
    text=" Issue / Return / Delete Books ",
    font=("Arial", 11, "bold"),
    bg="white",
    padx=12,
    pady=12
)
action_frame.pack(fill="x", pady=10)

tk.Label(
    action_frame,
    text="Student Name:",
    bg="white"
).pack(side="left", padx=5)

student_entry = ttk.Entry(action_frame, width=23)
student_entry.pack(side="left", padx=5)

ttk.Button(
    action_frame,
    text="Issue Book",
    command=issue_book
).pack(side="left", padx=8)

ttk.Button(
    action_frame,
    text="Return Book",
    command=return_book
).pack(side="left", padx=5)

ttk.Button(
    action_frame,
    text="Delete Book",
    command=delete_book
).pack(side="left", padx=8)

# 13. APPLICATION STARTUP AND SHUTDOWN

def on_closing():
    conn.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

refresh_books()
root.mainloop()
