import os
from dotenv import load_dotenv
import psycopg2
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template, request, redirect

load_dotenv()

app = Flask(__name__)

# get_db_connection() — a reusable function that opens a database connection. We'll call this every time we need to query data.
def get_db_connection():
    # psycopg2 — the library that connects Python to PostgreSQL. Think of it like the phone line between your app and the database.
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

# This is the bridge between your database and your Python code.
def run_query(query):
    # opens the database connection
    conn = get_db_connection()
    # runs the SQL query and loads the results directly into a pandas DataFrame
    df = pd.read_sql(query, conn)
    # closes the connection when done
    conn.close()
    # hands the DataFrame back to whatever called the function
    return df

def create_chart(x, y, title, xlabel, ylabel, color, chart_type="bar"):
    fig, ax = plt.subplots(figsize=(10,5))
    # it lets you choose between a bar chart or a line chart when you call the function.
    if chart_type == "bar":
        ax.bar(x, y, color=color)
    elif chart_type == "line":
        ax.plot(x, y, color=color, linewidth=2.5, marker='o')
    
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return image

@app.route("/")
def index():
    # Sales data
    sales_df = run_query("SELECT * FROM sales ORDER BY id")

    # Summary stats
    totals = run_query("""
        SELECT
            SUM(revenue) AS total_revenue,
            SUM(expenses) AS total_expenses,
            SUM(revenue - expenses) AS total_profit,
            ROUND(AVG(customers)) AS avg_monthly_customers
        FROM sales
    """)

    # Department data
    dept_df = run_query("SELECT * FROM departments ORDER BY budget DESC")

    # Charts
    revenue_chart = create_chart(
        sales_df["month"], sales_df["revenue"],
        "Monthly Revenue", "Month", "Revenue ($)", "#06b6d4"
    )
    profit_chart = create_chart(
        sales_df["month"], sales_df["revenue"],
        "Monthly Profit", "Month", "Profit ($)", "#10b981", chart_type="line"
    )
    customers_chart = create_chart(
        sales_df["month"], sales_df["customers"],
        "Monthly Customers", "Month", "Customers", "#8b5cf6", chart_type="line"
    )

    # sends the HTML page to the browser
    return render_template("index.html",
        # iloc[0] grabs the first row as a Series so we can access individual values like totals["total_revenue"] in the template.
        totals=totals.iloc[0],
        # Left side (sales_df=) — the name the HTML template will use to access the data. You could call it anything 
        # Right side (=sales_df) — the actual Python variable that holds the data, the one you created earlier with run_query()
        sales_df=sales_df,
        dept_df=dept_df,
        revenue_chart=revenue_chart,
        profit_chart=profit_chart,
        customers_chart=customers_chart
        )

@app.route("/add", methods=["GET","POST"])
def add_sale():
    if request.method == "POST":
        month = request.form["month"]
        year = request.form["year"]
        revenue = request.form["revenue"]
        expenses = request.form["expenses"]
        customers = request.form["customers"]

        conn = get_db_connection()
        # creates a cursor, which is the tool you use to execute SQL commands. Think of the connection (conn) as the phone call to the database, and the cursor as the person actually talking.
        cur = conn.cursor()
        # runs the SQL INSERT statement. The %s are placeholders — they get replaced with the actual values from the form. This is intentional — never put form values directly into a SQL string because it opens you up to SQL injection attacks.
        cur.execute(
            "INSERT INTO sales (month, year, revenue, expenses, customers) VALUES (%s, %s," \
            "%s, %s, %s)", (month, year, revenue, expenses, customers)
        )
        # saves the changes to the database permanently. Without this, the INSERT happens in memory but never gets written to disk. Like saving a Word document.
        conn.commit()
        # clean up after yourself. Close the cursor then the connection to free up resources.
        cur.close()
        conn.close()
        # after the form is submitted, send the user back to the homepage so they can see the updated data.
        return redirect("/")
    return render_template("add.html")

if __name__ == "__main__":
    app.run(debug=True)