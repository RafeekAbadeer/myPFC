from sqlite3 import Error
import tkinter.ttk as ttk
import tkinter as tk
from tkinter import messagebox
import sqlite3

column_headers = {
    "id": "ID",
    "account_name": "Account Name",
    "category_name": "Category Name",
    "description": "Description",
    # Add more column names as needed
}

def display_data(table_name, content_frame):
    # Clear the content frame
    for widget in content_frame.winfo_children():
        widget.destroy()

    # Create a frame to hold the menu bar and table
    frame = ttk.Frame(content_frame)
    frame.pack(fill=tk.BOTH, expand=True)

    # Create a menu bar with add, edit, and delete buttons
    menu_bar = ttk.Frame(frame)
    menu_bar.pack(fill=tk.X)

    add_button = ttk.Button(menu_bar, text="Add")
    add_button.pack(side=tk.LEFT)

    edit_button = ttk.Button(menu_bar, text="Edit")
    edit_button.pack(side=tk.LEFT)

    delete_button = ttk.Button(menu_bar, text="Delete")
    delete_button.pack(side=tk.LEFT)

    # Create a table to display the data
    data_table = ttk.Treeview(frame, show="headings")
    data_table.pack(fill=tk.BOTH, expand=True)

    try:
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM {table_name}")

        # Get the column names from the cursor
        column_names = [description[0] for description in cursor.description]

        # Create the table columns
        data_table["columns"] = column_names

        # Format the columns
        for column in column_names:
            data_table.column(column, anchor=tk.W, width=200)

        # Create headings for the columns
        for column in column_names:
            data_table.heading(column, text=column_headers.get(column, column))

        # Insert the data into the table
        rows = cursor.fetchall()
        for row in rows:
            data_table.insert("", "end", values=row)

        conn.close()
    except Error as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

if __name__ == "__main__":
    # Example usage of display_data
    root = tk.Tk()
    root.title("Data Display Example")
    root.geometry("800x600")

    content_frame = ttk.Frame(root)
    content_frame.pack(fill=tk.BOTH, expand=True)

    display_data("cat", content_frame)

    root.mainloop()
