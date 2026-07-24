# 🏥 AI-Driven Electronic Health Record (EHR) Management System

# 📖 About the Project
The AI-Driven Electronic Health Record (EHR) Management System is a web-based healthcare application developed using Python (Flask). It enables patients to securely upload medical reports in PDF or image format, extracts text using Tesseract OCR, processes medical information, analyzes health parameters using a rule-based approach, and generates health risk levels along with report summaries.
The system also provides role-based authentication for patients and doctors, centralized storage of electronic health records, and appointment management to improve healthcare accessibility and efficiency.

# ✨ Features
👤 Patient & Doctor Registration/Login
🔐 Secure Role-Based Authentication
📄 Upload Medical Reports (PDF/Image)
🔍 OCR-Based Text Extraction using Tesseract OCR
🧠 Medical Text Processing
📊 Rule-Based Health Risk Analysis
📝 Automatic Report Summary Generation
📁 Electronic Health Record Management
📅 Appointment Booking & Management
👨‍⚕️ Doctor Dashboard to View Patient Records
💾 Secure Data Storage using SQLite

# 🛠️ Tech Stack
1. Frontend
2. HTML
3. CSS
4. Bootstrap
5. Backend
6. Python
7. Flask
# Database
SQLite
# Libraries & Tools
1. Tesseract OCR
2. PyPDF2
3. Pillow (PIL)
4. Regular Expressions (Regex)

# ⚙️ Project Workflow
1. User registers as a Patient or Doctor.
2. User logs into the system.
3. Patient uploads a medical report (PDF/Image).
4. OCR extracts text from the uploaded report.
5. Medical information is processed.
6. Health parameters are analyzed using predefined medical rules.
7. A Health Risk Score (Low, Medium, High) is generated.
8. A summary of the report is created.
9. Patient records are securely stored in the database.
10. Doctors can review patient records and manage appointments.

# 🚀 Installation
1. Clone the repository
git clone https://github.com/Chinmay02-04/AI_EHR_System.git

2. Move to the project folder
cd AI_EHR_System

3. Install dependencies
pip install -r requirements.txt

4. Run the application
python app.py

5. Open your browser
http://127.0.0.1:5000
