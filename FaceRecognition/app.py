from flask import Flask, render_template
from flask import request, redirect, url_for, Response, flash
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import os
import cv2
from datetime import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
from detection.face_matching import detect_faces, align_face
from detection.face_matching import extract_features, match_face
from utils.configuration import load_yaml
from flask import jsonify
from datetime import datetime

matched_student_name = None
config_file_path = load_yaml("configs/database.yaml")

TEACHER_PASSWORD_HASH = config_file_path["teacher"]["password_hash"]
# print(TEACHER_PASSWORD_HASH)

# Initialize Firebase
cred = credentials.Certificate(config_file_path["firebase"]["pathToServiceAccount"])
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": config_file_path["firebase"]["databaseURL"],
        "storageBucket": config_file_path["firebase"]["storageBucket"],
    },
)


def upload_database(filename):
    try:
        bucket = storage.bucket()
        
        # Check if file already exists in Firebase Storage
        if bucket.get_blob(filename):
            error = f"<h1>{filename} already exists in the database</h1>"
            return True, error

        # Check if filename (without extension) is a number
        if not filename[:-4].isdigit():
            error = f"<h1>Please make sure that the name of the {filename} is a number</h1>"
            return True, error

        # Local file path (where the file is stored on your server)
        local_file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        
        # Check if local file exists
        if not os.path.exists(local_file_path):
            error = f"<h1>Local file {filename} not found</h1>"
            return True, error
        
        # Firebase Storage path (just the filename)
        blob = bucket.blob(filename)
        
        # Upload the file from local path to Firebase Storage
        blob.upload_from_filename(local_file_path)
        
        return False, None  # Success
        
    except Exception as e:
        error = f"<h1>Error uploading to Firebase: {str(e)}</h1>"
        return True, error
    
def match_with_database(img, database):
    '''The function "match_with_database" takes an image and a database as input, detects faces in the
    image, aligns and extracts features from each face, and matches the face to a face in the database.
    '''
    global matched_student_name  # Use a more descriptive global variable name
    
    # Detect faces in the frame
    faces = detect_faces(img)

    # Draw the rectangle around each face
    for x, y, w, h in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 4)

    # save the image
    cv2.imwrite("static/recognized/recognized.png", img)

    for face in faces:
        try:
            # Align the face
            aligned_face = align_face(img, face)

            # Extract features from the face
            embedding = extract_features(aligned_face)

            embedding = embedding[0]["embedding"]

            # Match the face to a face in the database
            match_result = match_face(embedding, database)

            if match_result is not None:
                matched_student_name = match_result  # Store the matched name globally
                return f"Match found: {match_result}"
            else:
                matched_student_name = None
                return "No match found"
        except:
            matched_student_name = None
            return "No face detected"

app = Flask(__name__, template_folder="template")
app.secret_key = "123456"  # Add this line

# Specify the directory to save uploaded images
UPLOAD_FOLDER = "static/images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/add_info")
def add_info():
    return render_template("add_info.html")


@app.route("/teacher_login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        password = request.form.get("password")
        if check_password_hash(TEACHER_PASSWORD_HASH, password):
            return redirect(url_for("attendance"))
        else:
            flash("Incorrect password")
    return render_template("teacher_login.html")


@app.route("/attendance")
def attendance():
    ref = db.reference("AttendanceHistory")
    attendance_data = ref.get()
    
    # Initialize empty dictionary for attendance history
    attendance_history = {}
    
    if attendance_data:
        # Get the number of attendance records
        number_records = len(attendance_data)
        
        # Loop through all attendance records
        for i in range(1, number_records + 1):
            try:
                record = db.reference(f"AttendanceHistory/{i}").get()
                if record:
                    # Get student details from Students table
                    student_id = record["studentId"]
                    student_info = db.reference(f"Students/{student_id}").get()
                    
                    if student_info:
                        attendance_history[i] = [
                            record["name"],                    # Position 0 - Name
                            student_info["email"],             # Position 1 - Email
                            student_info["userType"],          # Position 2 - Type
                            record["status"],                  # Position 3 - Status
                            record["timestamp"]                # Position 4 - Timestamp
                        ]
            except (KeyError, TypeError):
                # Skip if record doesn't exist or is malformed
                continue
    
    return render_template("attendance.html", students=attendance_history)

@app.route("/upload", methods=["POST"])
def upload():
    global filename
    # Check if a file was uploaded
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]

    # Check if the file is one of the allowed types/extensions
    if file.filename == "":
        return "No selected file", 400

    if file and allowed_file(file.filename):
        # Make the filename safe, remove unsupported chars
        filename = secure_filename(file.filename)
        # change the name of the file to the studentId
        # Information to database
        ref = db.reference("Students")
        try:
            # Obtain the last studentId number from the database
            studentId = len(ref.get())
        except TypeError:
            studentId = 1

        filename = f"{studentId}.png"

        # Move the file from the temporal folder to
        # the upload folder we setup
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Upload the file to the database
        val, err = upload_database(filename)

        if val:
            return err

        # Redirect the user to the uploaded_file route, which
        # will basically show on the browser the uploaded file
        return redirect(url_for("add_info"))

    return "File upload failed", 400


def allowed_file(filename):
    # Put your allowed file types here
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # for browser cache
    # Generate the URL of the image
    url = url_for("static", filename="images/" + filename, v=timestamp)
    # Return an HTML string that includes an <img> tag
    return f'<h1>File uploaded successfully</h1><img src="{url}" alt="Uploaded image">'


@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/capture", methods=["POST"])
def capture():
    global filename
    ret, frame = video.read()
    if ret:
        # Information to database
        ref = db.reference("Students")

        try:
            # Obtain the last studentId number from the database
            studentId = len(ref.get())

        except TypeError:
            studentId = 1

        # Save the image
        filename = f"{studentId}.png"
        # Save the frame as an image
        cv2.imwrite(os.path.join(app.config["UPLOAD_FOLDER"], filename), frame)

        # Upload the file to the database
        val, err = upload_database(filename)

        if val:
            return err
    # Redirect to the success page
    return redirect(url_for("add_info"))


@app.route("/success/<filename>")
def success(filename):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # for browser cache
    # Generate the URL of the image
    url = url_for("static", filename="images/" + filename, v=timestamp)
    # Return an HTML string that includes an <img> tag
    return f'<h1>{filename} image uploaded successfully to the database</h1><img src="{url}" alt="Uploaded image">'


@app.route("/submit_info", methods=["POST"])
def submit_info():
    global filename
    # Get the form data
    name = request.form.get("name")
    email = request.form.get("email")
    userType = request.form.get("userType")
    password = request.form.get("password")
    attendanceStatus = "Out"
    # Get the current time
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Get the last uploaded image
    studentId, _ = os.path.splitext(filename)
    fileName = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    data = cv2.imread(fileName)

    faces = detect_faces(data)
    if len(faces) == 0:
        return jsonify({"status": "error", "message": "No face detected. Please upload a clearer image with a visible face."})

    for face in faces:
        aligned_face = align_face(data, face)
        embedding = extract_features(aligned_face)
        if embedding is None:
            return jsonify({"status": "error", "message": "Error in face recognition. Please ensure the image contains a clear face."})
        
        # NEW CODE: Check if face already exists in database
        ref = db.reference("Students")
        try:
            existing_students = ref.get()
            if existing_students:
                # Create database for matching
                database = {}
                for student_id, student_info in existing_students.items():
                    if 'embeddings' in student_info:
                        database[student_info['name']] = student_info['embeddings']
                
                # Check if current face matches any existing face
                match_result = match_face(embedding[0]["embedding"], database)
                if match_result is not None:
                    # Delete the uploaded image since registration is not allowed
                    if os.path.exists(fileName):
                        os.remove(fileName)
                    return jsonify({
                        "status": "error", 
                        "message": f"Face already registered in the system as '{match_result}'. Duplicate registration not allowed."
                    })
        except Exception as e:
            print(f"Error checking existing faces: {e}")
        
        break

    # If no match found, proceed with registration
    ref = db.reference("Students")
    student_data = {
        str(studentId): {
            "name": name,
            "email": email,
            "userType": userType,
            "attendanceStatus": attendanceStatus,
            "password": password,
            "embeddings": embedding[0]["embedding"],
            "timestamp": timestamp
        }
    }

    for key, value in student_data.items():
        ref.child(key).set(value)

    # Return a success JSON response instead of redirecting
    return jsonify({"status": "success", "message": f"Information for {name} successfully uploaded!"})

@app.route("/recognize", methods=["GET", "POST"])
def recognize():
    global matched_student_name
    ret, frame = video.read()
    if ret:
        ref = db.reference("Students")
        number_student = len(ref.get())
        database = {}
        for i in range(1, number_student):
            studentInfo = db.reference(f"Students/{i}").get()
            studentName = studentInfo["name"]
            studentEmbedding = studentInfo["embeddings"]
            database[studentName] = studentEmbedding
        detection = match_with_database(frame, database)
        if matched_student_name:
            # Find the correct student ID
            matched_student_id = None
            for student_id in range(1, number_student):
                student_info = db.reference(f"Students/{student_id}").get()
                if student_info and student_info.get("name") == matched_student_name:
                    matched_student_id = student_id
                    break
            if matched_student_id:
                student_ref = db.reference(f"Students/{matched_student_id}")
                student_info = student_ref.get()
                current_status = student_info.get("attendanceStatus", "Out")
                new_status = "Out" if current_status == "In" else "In"
                current_time = datetime.now().strftime("%I:%M %p")
                student_ref.update({
                    "attendanceStatus": new_status,
                    "attendanceTime": current_time
                })
                # Add entry to AttendanceHistory
                history_ref = db.reference("AttendanceHistory")
                try:
                    history_count = len(history_ref.get()) if history_ref.get() else 0
                except TypeError:
                    history_count = 0
                history_data = {
                    str(history_count + 1): {
                        "studentId": str(matched_student_id),
                        "name": matched_student_name,
                        "status": new_status,
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
                for key, value in history_data.items():
                    history_ref.child(key).set(value)
                return {
                    "status": new_status,
                    "name": matched_student_name,
                    "time": current_time
                }
            else:
                return {"status": "Not Registered"}
        else:
            return {"status": "Not Registered"}
    return redirect(url_for("home"))


def gen_frames():
    global video
    video = cv2.VideoCapture(0)
    while True:
        success, frame = video.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


if __name__ == "__main__":
    app.run(debug=True)
