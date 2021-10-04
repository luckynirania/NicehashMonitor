from flask import Flask
from flask import render_template
from datetime import time
import sqlite3

 
app = Flask(__name__)
 
@app.route("/simple_chart")
def chart():
    data = []
    conn = sqlite3.connect('./database.db')
    cur = conn.cursor()
    cur.execute("SELECT UUID FROM SUMMARY")

    rows = cur.fetchall()

    ls = []
    UUID_HASHRATEMINER_PAIR = []

    for each in rows:
        cur = conn.cursor()
        cur.execute("SELECT * FROM STATS WHERE UUID=?", (each[0],))
        temp = cur.fetchall()
        ls.append(temp)

        temp2 = []
        for every in temp:
            temp2.append([int(every[0]) * 1000, float(every[2])])
        UUID_HASHRATEMINER_PAIR.append(temp2)

    print(UUID_HASHRATEMINER_PAIR[0])

    conn.close()
    
    TotalCharts = len(ls)
    return render_template('./chart.html', count=TotalCharts, data=UUID_HASHRATEMINER_PAIR)
 
if __name__ == "__main__":
    app.run(debug=True)