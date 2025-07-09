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
    ref = db.reference("Students")
    number_student = len(ref.get())
    # attandence
    students = {}
    for i in range(1, number_student):
        studentInfo = db.reference(f"Students/{i}").get()
        students[i] = [
            studentInfo["name"],
            studentInfo["email"],
            studentInfo["userType"],
           studentInfo["attendanceStatus"],
        ]
    return render_template("attendance.html", students=students)


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
    # Get the form data
    name = request.form.get("name")
    email = request.form.get("email")
    userType = request.form.get("userType")
    password = request.form.get("password")
    attendanceStatus = "Out"  # Default attendance status

    # Get the last uploaded image
    studentId, _ = os.path.splitext(filename)
    fileName = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    data = cv2.imread(fileName)

    # Detect faces in the image
    faces = detect_faces(data)

    # Explicitly check if faces is empty
    if len(faces) == 0:
        return "<h2>No face detected. Please upload a clearer image with a visible face.</h2>"

    # Process each face (in case there are multiple faces, though unlikely)
    for face in faces:
        # Align the face
        aligned_face = align_face(data, face)

        # Extract features from the face
        embedding = extract_features(aligned_face)
        if embedding is None:
            return "<h2>Error in face recognition. Please ensure the image contains a clear face.</h2>"

        break  # Assuming the first face is the one we want

    # Add the information to the database
    ref = db.reference("Students")
    data = {
        str(studentId): {
            "name": name,
            "email": email,
            "userType": userType,
            "attendanceStatus": attendanceStatus,
            "password": password,
            "embeddings": embedding[0]["embedding"],
        }
    }

    for key, value in data.items():
        ref.child(key).set(value)

    return redirect(url_for("success", filename=filename))


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
            # Retrieve the current attendance status
            student_ref = db.reference(f"Students/{i}")
            student_info = student_ref.get()
            current_status = student_info.get("attendanceStatus", "Out")

            # Toggle attendance status
            if current_status == "In":
                new_status = "Out"
            else:
                new_status = "In"

            # Update the attendance status and the current time
            current_time = datetime.now().strftime("%I:%M %p")
            student_ref.update({
                "attendanceStatus": new_status,
                "attendanceTime": current_time  # Store the time when the attendance is marked
            })

            # Return the status and time to the frontend
            return {
                "status": new_status,
                "name": matched_student_name,
                "time": current_time
            }
        else:
            # If no student matched, return an error response
            return {"status": "Not Registered"}

    return redirect(url_for("home"))  # If no face detected, return home or another page.


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
