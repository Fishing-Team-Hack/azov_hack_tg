import sqlite3
from flask import Flask, request, jsonify, send_file
import pandas as pd
from io import BytesIO

app = Flask(__name__)


@app.route('/photos', methods=['GET'])
def get_photos():
    conn = sqlite3.connect('mollusk_database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM MolluskData')
    Mollusks = c.fetchall()
    conn.close()
    return jsonify(
        [{'UserID': Mollusk[0], 'PhotoData': Mollusk[1], 'Latitude': Mollusk[2], 'Longitude': Mollusk[3]} for Mollusk in Mollusks])


@app.route('/photos', methods=['POST'])
def add_photo():
    data = request.get_json()
    conn = sqlite3.connect('mollusk_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO MolluskData (UserID, PhotoData, Latitude, Longitude, UserID) VALUES (?, ?, ?, ?)',
              (data['UserID'], data['PhotoData'], data['Latitude'], data['Longitude']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Photo added successfully'})


@app.route('/photos/download', methods=['GET'])
def download_photos():
    conn = sqlite3.connect('mollusk_database.db')
    df = pd.read_sql_query('SELECT * FROM MolluskData', conn)
    conn.close()

    # Создаем объект BytesIO для записи данных в память
    output = BytesIO()

    # Записываем данные в формате XLSX
    df.to_excel(output, index=False)

    # Возвращаем файл клиенту с нужными заголовками
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='Mollusk.xlsx')


if __name__ == '__main__':
    app.run(debug=True)
