from flask import Flask, request, jsonify
import sqlite3
import pandas as pd
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = "questions.db"

# 初始化資料庫
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            options TEXT,
            correct_answer TEXT,
            explanation TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 取得題目 API
@app.route('/get_questions', methods=['GET'])
def get_questions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, options FROM questions")
    questions = [{"id": row[0], "question": row[1], "options": eval(row[2])} for row in cursor.fetchall()]
    conn.close()
    return jsonify(questions)

# 上傳 CSV/Excel 題庫
@app.route('/upload_questions', methods=['POST'])
def upload_questions():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    ext = os.path.splitext(file.filename)[1]
    if ext not in ['.csv', '.xlsx']:
        return jsonify({"error": "Invalid file format"}), 400

    try:
        df = pd.read_csv(file) if ext == '.csv' else pd.read_excel(file)
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 400

    column_mapping = {
        "題目": "question",
        "正確答案": "correct_answer",
        "解釋": "explanation"
    }
    
    df.rename(columns=column_mapping, inplace=True)

    if "question" not in df.columns:
        return jsonify({"error": "Missing column: question"}), 400

    options_columns = ["選項A", "選項B", "選項C", "選項D"]
    df["options"] = df.apply(lambda row: [row.get(col, "") for col in options_columns], axis=1)

    correct_mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
    df["correct_answer"] = df.apply(lambda row: row["options"][correct_mapping.get(row["correct_answer"], 0)], axis=1)

    df["explanation"] = df["explanation"].fillna("")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("INSERT INTO questions (question, options, correct_answer, explanation) VALUES (?, ?, ?, ?)", 
                       (row["question"], str(row["options"]), row["correct_answer"], row["explanation"]))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Questions uploaded successfully"})

# 驗證答案 API
@app.route('/check_answer', methods=['POST'])
def check_answer():
    data = request.json
    question_id = data.get('id')
    user_answer = data.get('answer')

    if not question_id or not user_answer:
        return jsonify({"error": "Missing data"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT correct_answer, explanation FROM questions WHERE id = ?", (question_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        correct = row[0] == user_answer
        return jsonify({"correct": correct, "explanation": row[1]})
    return jsonify({"error": "Question not found"}), 404

# 清空所有題目 API
@app.route('/clear_questions', methods=['POST'])
def clear_questions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions")  # 刪除所有題目
    conn.commit()
    conn.close()
    return jsonify({"message": "All questions have been deleted"})

if __name__ == '__main__':
    app.run(debug=True)
