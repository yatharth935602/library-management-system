# Library Management System

A desktop-based Library Management System developed using Python, Tkinter, and SQLite. This project helps manage book records and track book issue and return activities through a graphical user interface.

## Features

- Add new books with Book ID, title, and author.
- Search books by title or author.
- Filter books by availability status.
- Issue available books to students.
- Return issued books.
- View total, available, and issued book statistics.
- Maintain book issue and return history.
- Prevent duplicate Book IDs and multiple active issues of the same book.
- Delete books that have no issue history.

## Technologies Used

- **Python** – Application programming language.
- **Tkinter** – Graphical User Interface (GUI).
- **SQLite3** – Database management.
- **Datetime** – Recording issue and return date-time.

## Database Structure

The project uses two tables:

- **books:** Stores Book ID, title, and author.
- **issues:** Stores issue ID, Book ID, student name, issue date, and return date.

The application uses a foreign key to connect the two tables. Book availability is determined from the active issue records.

## How to Run

1. Install Python 3 on your computer.
2. Download or clone this repository.
3. Open the project folder in a terminal.
4. Run the following command:

```bash
python main.py
```

The SQLite database file `library.db` is created automatically when the application runs for the first time.

## Project Team

- **Yatharth Singh** – B24CS015
- **Deepansh Sah** – B24CS010
- **Aman Verma** – B24CS017
- **Ajay Raj Yadav** – B24CS011

## Project Information

This project was developed as part of an academic Python programming project.

