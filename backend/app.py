# from flask import Flask, render_template, request, send_from_directory, redirect, url_for
# import numpy as np
# import cv2
# from tensorflow.keras.models import load_model
# from tensorflow.keras.preprocessing import image
# import tensorflow as tf
# import sqlite3
# import os
# import base64
# from io import BytesIO
# from datetime import datetime

# # -------------------------------------------------
# # Flask App
# # -------------------------------------------------
# app = Flask(__name__, template_folder="../frontend")

# # -------------------------------------------------
# # Paths
# # -------------------------------------------------
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# MODEL_PATH = os.path.join(BASE_DIR, "vgg16_best.h5")
# DB_PATH = os.path.join(BASE_DIR, "smart_diagnosis.db")
# UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

# os.makedirs(UPLOAD_DIR, exist_ok=True)

# # -------------------------------------------------
# # Load Model
# # -------------------------------------------------
# print("Loading model...")
# model = load_model(MODEL_PATH)

# class_labels = [
#     "adenocarcinoma",
#     "large.cell.carcinoma",
#     "normal",
#     "squamous.cell.carcinoma"
# ]

# # -------------------------------------------------
# # GradCAM Function
# # -------------------------------------------------
# def get_gradcam(img_array, model):

#     # Automatically find last conv layer
#     last_conv_layer = None
#     for layer in reversed(model.layers):
#         if "conv" in layer.name:
#             last_conv_layer = layer.name
#             break

#     grad_model = tf.keras.models.Model(
#         inputs=model.inputs,
#         outputs=[model.get_layer(last_conv_layer).output, model.output]
#     )

#     img_tensor = tf.convert_to_tensor(img_array)

#     with tf.GradientTape() as tape:

#         conv_outputs, predictions = grad_model([img_tensor])

#         predictions = tf.reshape(predictions, [-1])

#         pred_index = tf.argmax(predictions)

#         loss = predictions[pred_index]

#     grads = tape.gradient(loss, conv_outputs)

#     pooled_grads = tf.reduce_mean(grads, axis=(0,1,2))

#     conv_outputs = conv_outputs[0]

#     heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)

#     heatmap = tf.maximum(heatmap, 0)

#     heatmap = heatmap / (tf.reduce_max(heatmap) + 1e-10)

#     return heatmap.numpy(), int(pred_index)

# # -------------------------------------------------
# # Cancer Stage Calculation
# # -------------------------------------------------
# def calculate_cancer_stage(heatmap):

#     heatmap = heatmap / (np.max(heatmap) + 1e-8)

#     threshold = 0.5

#     tumor_pixels = np.sum(heatmap > threshold)

#     total_pixels = heatmap.size

#     coverage = (tumor_pixels / total_pixels) * 100

#     if coverage <= 10:
#         stage = "Stage I"
#     elif coverage <= 25:
#         stage = "Stage II"
#     elif coverage <= 45:
#         stage = "Stage III"
#     else:
#         stage = "Stage IV"

#     return round(coverage,2), stage

# # -------------------------------------------------
# # Database
# # -------------------------------------------------
# def get_db():

#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     return conn


# def init_db():

#     conn = get_db()

#     conn.execute(
#         """
#         CREATE TABLE IF NOT EXISTS patients(
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         patient_name TEXT,
#         age INTEGER,
#         gender TEXT,
#         smoking TEXT,
#         scan_path TEXT,
#         gradcam_path TEXT,
#         prediction TEXT,
#         confidence REAL,
#         stage TEXT,
#         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#         )
#         """
#     )

#     conn.commit()
#     conn.close()

# init_db()

# # -------------------------------------------------
# # Routes
# # -------------------------------------------------
# @app.route("/")
# def welcome():
#     return render_template("welcome.html")


# @app.route("/analyze")
# def analyze():
#     return render_template("analyze.html")


# @app.route("/admin")
# def admin():

#     conn = get_db()

#     patients = conn.execute(
#         "SELECT * FROM patients ORDER BY timestamp DESC"
#     ).fetchall()

#     conn.close()

#     return render_template("admin.html", patients=patients)

# # -------------------------------------------------
# # Prediction Route
# # -------------------------------------------------
# @app.route("/predict", methods=["POST"])
# def predict():

#     patient_name = request.form.get("patient_name")
#     age = request.form.get("age")
#     gender = request.form.get("gender")
#     smoking = request.form.get("smoking")

#     file = request.files.get("scan")

#     if not file:
#         return "No file uploaded", 400

#     img = image.load_img(BytesIO(file.read()), target_size=(224,224))

#     img_array = image.img_to_array(img)

#     img_array_norm = np.expand_dims(img_array, axis=0) / 255.0

#     preds = model.predict(img_array_norm)[0]

#     pred_index = int(np.argmax(preds))

#     pred_label = class_labels[pred_index]

#     confidence = float(np.max(preds) * 100)

#     confidences = {class_labels[i]: float(preds[i]) for i in range(len(class_labels))}

#     # Invalid image detection
#     if confidence < 90:

#         return render_template(
#             "results.html",
#             patient_name=patient_name,
#             prediction="Invalid Image (Not Lung CT)",
#             confidence="0",
#             coverage="0",
#             stage="N/A",
#             confidences={},
#             gradcam=None,
#             original=None,
#             age=age,
#             gender=gender,
#             smoking=smoking
#         )

#     # GradCAM
#     heatmap, _ = get_gradcam(img_array_norm, model)

#     original = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

#     heatmap = cv2.resize(heatmap, (original.shape[1], original.shape[0]))

#     coverage, stage = calculate_cancer_stage(heatmap)

#     heatmap_uint8 = np.uint8(255 * heatmap)

#     heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

#     gradcam = cv2.addWeighted(original, 0.6, heatmap_color, 0.4, 0)

#     timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

#     scan_file = f"scan_{timestamp}.png"
#     gradcam_file = f"gradcam_{timestamp}.png"

#     cv2.imwrite(os.path.join(UPLOAD_DIR, scan_file), original)
#     cv2.imwrite(os.path.join(UPLOAD_DIR, gradcam_file), gradcam)

#     conn = get_db()

#     conn.execute(
#         """
#         INSERT INTO patients
#         (patient_name,age,gender,smoking,scan_path,gradcam_path,prediction,confidence,stage)
#         VALUES(?,?,?,?,?,?,?,?,?)
#         """,
#         (
#             patient_name,
#             age,
#             gender,
#             smoking,
#             scan_file,
#             gradcam_file,
#             pred_label,
#             confidence,
#             stage
#         ),
#     )

#     conn.commit()
#     conn.close()

#     _, buf1 = cv2.imencode(".png", gradcam)
#     gradcam_base64 = base64.b64encode(buf1).decode("utf-8")

#     _, buf2 = cv2.imencode(".png", original)
#     original_base64 = base64.b64encode(buf2).decode("utf-8")

#     return render_template(
#         "results.html",
#         patient_name=patient_name,
#         prediction=pred_label,
#         confidence=f"{confidence:.2f}%",
#         coverage=f"{coverage}%",
#         stage=stage,
#         confidences=confidences,
#         gradcam=gradcam_base64,
#         original=original_base64,
#         age=age,
#         gender=gender,
#         smoking=smoking
#     )

# # -------------------------------------------------
# # Serve Uploaded Images
# # -------------------------------------------------
# @app.route("/uploads/<filename>")
# def uploaded_file(filename):
#     return send_from_directory(UPLOAD_DIR, filename)

# # -------------------------------------------------
# # Delete Patient
# # -------------------------------------------------

# @app.route("/admin/delete/<int:patient_id>", methods=["POST"])
# def delete_patient(patient_id):

#     conn = get_db()

#     row = conn.execute(
#         "SELECT scan_path, gradcam_path FROM patients WHERE id=?",
#         (patient_id,)
#     ).fetchone()

#     if row:

#         scan_path = os.path.join(UPLOAD_DIR, row["scan_path"])
#         gradcam_path = os.path.join(UPLOAD_DIR, row["gradcam_path"])

#         if os.path.exists(scan_path):
#             os.remove(scan_path)

#         if os.path.exists(gradcam_path):
#             os.remove(gradcam_path)

#         conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))
#         conn.commit()

#     conn.close()

#     return redirect(url_for("admin"))

# # -------------------------------------------------
# # Run Server
# # -------------------------------------------------
# # if __name__ == "__main__":
#     # app.run(debug=True, port=5001)

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 10000))
#     app.run(host="0.0.0.0", port=port)










# from flask import Flask, render_template, request, send_from_directory, redirect, url_for
# import numpy as np
# import cv2
# import tensorflow as tf
# from tensorflow.keras.models import load_model
# from tensorflow.keras.preprocessing import image
# import sqlite3
# import os
# import base64
# from io import BytesIO
# from datetime import datetime
# import gdown
# from keras.models import load_model

# # Silence tensorflow logs
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# # -------------------------------------------------
# # Flask App
# # -------------------------------------------------
# app = Flask(__name__, template_folder="../frontend")

# # -------------------------------------------------
# # Paths
# # -------------------------------------------------
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# MODEL_PATH = os.path.join(BASE_DIR, "vgg16_best.h5")
# DB_PATH = os.path.join(BASE_DIR, "smart_diagnosis.db")
# UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

# os.makedirs(UPLOAD_DIR, exist_ok=True)

# # -------------------------------------------------
# # Download model if not exists
# # -------------------------------------------------
# if not os.path.exists(MODEL_PATH):

#     print("Downloading model from Google Drive...")

#     url = "https://drive.google.com/uc?id=1-WjoNcXK3-ZHguI4szr1jNFzSbgPErHG"

#     gdown.download(url, MODEL_PATH, quiet=False)



# # -------------------------------------------------
# # Load Model
# # -------------------------------------------------
# print("Loading model...")



# model = load_model(MODEL_PATH, compile=False, safe_mode=False)

# print("Model loaded successfully")

# class_labels = [
#     "adenocarcinoma",
#     "large.cell.carcinoma",
#     "normal",
#     "squamous.cell.carcinoma"
# ]

# # -------------------------------------------------
# # GradCAM Function
# # -------------------------------------------------
# def get_gradcam(img_array, model):

#     last_conv_layer = None

#     for layer in reversed(model.layers):
#         if "conv" in layer.name:
#             last_conv_layer = layer.name
#             break

#     grad_model = tf.keras.models.Model(
#         inputs=model.inputs,
#         outputs=[model.get_layer(last_conv_layer).output, model.output]
#     )

#     img_tensor = tf.convert_to_tensor(img_array)

#     with tf.GradientTape() as tape:

#         conv_outputs, predictions = grad_model([img_tensor])

#         predictions = tf.reshape(predictions, [-1])

#         pred_index = tf.argmax(predictions)

#         loss = predictions[pred_index]

#     grads = tape.gradient(loss, conv_outputs)

#     pooled_grads = tf.reduce_mean(grads, axis=(0,1,2))

#     conv_outputs = conv_outputs[0]

#     heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)

#     heatmap = tf.maximum(heatmap, 0)

#     heatmap = heatmap / (tf.reduce_max(heatmap) + 1e-10)

#     return heatmap.numpy(), int(pred_index)

# # -------------------------------------------------
# # Cancer Stage Calculation
# # -------------------------------------------------
# def calculate_cancer_stage(heatmap):

#     heatmap = heatmap / (np.max(heatmap) + 1e-8)

#     threshold = 0.5

#     tumor_pixels = np.sum(heatmap > threshold)

#     total_pixels = heatmap.size

#     coverage = (tumor_pixels / total_pixels) * 100

#     if coverage <= 10:
#         stage = "Stage I"
#     elif coverage <= 25:
#         stage = "Stage II"
#     elif coverage <= 45:
#         stage = "Stage III"
#     else:
#         stage = "Stage IV"

#     return round(coverage,2), stage

# # -------------------------------------------------
# # Database
# # -------------------------------------------------
# def get_db():

#     conn = sqlite3.connect(DB_PATH)

#     conn.row_factory = sqlite3.Row

#     return conn


# def init_db():

#     conn = get_db()

#     conn.execute(
#         """
#         CREATE TABLE IF NOT EXISTS patients(
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         patient_name TEXT,
#         age INTEGER,
#         gender TEXT,
#         smoking TEXT,
#         scan_path TEXT,
#         gradcam_path TEXT,
#         prediction TEXT,
#         confidence REAL,
#         stage TEXT,
#         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#         )
#         """
#     )

#     conn.commit()

#     conn.close()

# init_db()

# # -------------------------------------------------
# # Routes
# # -------------------------------------------------
# @app.route("/")
# def welcome():

#     return render_template("welcome.html")


# @app.route("/analyze")
# def analyze():

#     return render_template("analyze.html")


# @app.route("/admin")
# def admin():

#     conn = get_db()

#     patients = conn.execute(
#         "SELECT * FROM patients ORDER BY timestamp DESC"
#     ).fetchall()

#     conn.close()

#     return render_template("admin.html", patients=patients)

# # -------------------------------------------------
# # Prediction Route
# # -------------------------------------------------
# @app.route("/predict", methods=["POST"])
# def predict():

#     patient_name = request.form.get("patient_name")
#     age = request.form.get("age")
#     gender = request.form.get("gender")
#     smoking = request.form.get("smoking")

#     file = request.files.get("scan")

#     if not file:
#         return "No file uploaded", 400

#     img = image.load_img(BytesIO(file.read()), target_size=(224,224))

#     img_array = image.img_to_array(img)

#     img_array_norm = np.expand_dims(img_array, axis=0) / 255.0

#     preds = model.predict(img_array_norm)[0]

#     pred_index = int(np.argmax(preds))

#     pred_label = class_labels[pred_index]

#     confidence = float(np.max(preds) * 100)

#     confidences = {class_labels[i]: float(preds[i]) for i in range(len(class_labels))}

#     heatmap, _ = get_gradcam(img_array_norm, model)

#     original = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

#     heatmap = cv2.resize(heatmap, (original.shape[1], original.shape[0]))

#     coverage, stage = calculate_cancer_stage(heatmap)

#     heatmap_uint8 = np.uint8(255 * heatmap)

#     heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

#     gradcam = cv2.addWeighted(original, 0.6, heatmap_color, 0.4, 0)

#     timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

#     scan_file = f"scan_{timestamp}.png"

#     gradcam_file = f"gradcam_{timestamp}.png"

#     cv2.imwrite(os.path.join(UPLOAD_DIR, scan_file), original)

#     cv2.imwrite(os.path.join(UPLOAD_DIR, gradcam_file), gradcam)

#     conn = get_db()

#     conn.execute(
#         """
#         INSERT INTO patients
#         (patient_name,age,gender,smoking,scan_path,gradcam_path,prediction,confidence,stage)
#         VALUES(?,?,?,?,?,?,?,?,?)
#         """,
#         (
#             patient_name,
#             age,
#             gender,
#             smoking,
#             scan_file,
#             gradcam_file,
#             pred_label,
#             confidence,
#             stage
#         ),
#     )

#     conn.commit()

#     conn.close()

#     _, buf1 = cv2.imencode(".png", gradcam)

#     gradcam_base64 = base64.b64encode(buf1).decode("utf-8")

#     _, buf2 = cv2.imencode(".png", original)

#     original_base64 = base64.b64encode(buf2).decode("utf-8")

#     return render_template(
#         "results.html",
#         patient_name=patient_name,
#         prediction=pred_label,
#         confidence=f"{confidence:.2f}%",
#         coverage=f"{coverage}%",
#         stage=stage,
#         confidences=confidences,
#         gradcam=gradcam_base64,
#         original=original_base64,
#         age=age,
#         gender=gender,
#         smoking=smoking
#     )

# # -------------------------------------------------
# # Serve Uploaded Images
# # -------------------------------------------------
# @app.route("/uploads/<filename>")
# def uploaded_file(filename):

#     return send_from_directory(UPLOAD_DIR, filename)

# # -------------------------------------------------
# # Delete Patient
# # -------------------------------------------------
# @app.route("/admin/delete/<int:patient_id>", methods=["POST"])
# def delete_patient(patient_id):

#     conn = get_db()

#     row = conn.execute(
#         "SELECT scan_path, gradcam_path FROM patients WHERE id=?",
#         (patient_id,)
#     ).fetchone()

#     if row:

#         scan_path = os.path.join(UPLOAD_DIR, row["scan_path"])

#         gradcam_path = os.path.join(UPLOAD_DIR, row["gradcam_path"])

#         if os.path.exists(scan_path):
#             os.remove(scan_path)

#         if os.path.exists(gradcam_path):
#             os.remove(gradcam_path)

#         conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))

#         conn.commit()

#     conn.close()

#     return redirect(url_for("admin"))

# # -------------------------------------------------
# # Run Server
# # -------------------------------------------------
# if __name__ == "__main__":

#     port = int(os.environ.get("PORT", 10000))

#     app.run(host="0.0.0.0", port=port)






import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import numpy as np
import cv2
import tensorflow as tf
import sqlite3
import base64
from io import BytesIO
from datetime import datetime
import gdown

# -------------------------------------------------
# FIX OLD MODEL COMPATIBILITY
# -------------------------------------------------
from keras.layers import InputLayer

old_init = InputLayer.__init__

def new_init(self, *args, **kwargs):
    kwargs.pop("batch_shape", None)
    old_init(self, *args, **kwargs)

InputLayer.__init__ = new_init

# -------------------------------------------------
# Flask App
# -------------------------------------------------
app = Flask(__name__, template_folder="../frontend")

# -------------------------------------------------
# Paths
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(BASE_DIR, "vgg16_best.h5")
DB_PATH = os.path.join(BASE_DIR, "smart_diagnosis.db")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------
# Download Model
# -------------------------------------------------
if not os.path.exists(MODEL_PATH):

    print("Downloading model from Google Drive...")

    url = "https://drive.google.com/uc?id=1-WjoNcXK3-ZHguI4szr1jNFzSbgPErHG"

    gdown.download(url, MODEL_PATH, quiet=False)

# -------------------------------------------------
# Load Model
# -------------------------------------------------
print("Loading model...")

model = tf.keras.models.load_model(MODEL_PATH, compile=False)

print("Model loaded successfully")

class_labels = [
    "adenocarcinoma",
    "large.cell.carcinoma",
    "normal",
    "squamous.cell.carcinoma"
]

# -------------------------------------------------
# GradCAM
# -------------------------------------------------
def get_gradcam(img_array, model):

    last_conv_layer = None

    for layer in reversed(model.layers):
        if "conv" in layer.name:
            last_conv_layer = layer.name
            break

    grad_model = tf.keras.models.Model(
        inputs=model.inputs,
        outputs=[model.get_layer(last_conv_layer).output, model.output]
    )

    img_tensor = tf.convert_to_tensor(img_array)

    with tf.GradientTape() as tape:

        conv_outputs, predictions = grad_model([img_tensor])

        predictions = tf.reshape(predictions, [-1])

        pred_index = tf.argmax(predictions)

        loss = predictions[pred_index]

    grads = tape.gradient(loss, conv_outputs)

    pooled_grads = tf.reduce_mean(grads, axis=(0,1,2))

    conv_outputs = conv_outputs[0]

    heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)

    heatmap = tf.maximum(heatmap, 0)

    heatmap = heatmap / (tf.reduce_max(heatmap) + 1e-10)

    return heatmap.numpy(), int(pred_index)

# -------------------------------------------------
# Cancer Stage
# -------------------------------------------------
def calculate_cancer_stage(heatmap):

    heatmap = heatmap / (np.max(heatmap) + 1e-8)

    threshold = 0.5

    tumor_pixels = np.sum(heatmap > threshold)

    total_pixels = heatmap.size

    coverage = (tumor_pixels / total_pixels) * 100

    if coverage <= 10:
        stage = "Stage I"
    elif coverage <= 25:
        stage = "Stage II"
    elif coverage <= 45:
        stage = "Stage III"
    else:
        stage = "Stage IV"

    return round(coverage,2), stage

# -------------------------------------------------
# Database
# -------------------------------------------------
def get_db():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn

def init_db():

    conn = get_db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS patients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        age INTEGER,
        gender TEXT,
        smoking TEXT,
        scan_path TEXT,
        gradcam_path TEXT,
        prediction TEXT,
        confidence REAL,
        stage TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()

    conn.close()

init_db()

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/analyze")
def analyze():
    return render_template("analyze.html")

@app.route("/admin")
def admin():

    conn = get_db()

    patients = conn.execute(
        "SELECT * FROM patients ORDER BY timestamp DESC"
    ).fetchall()

    conn.close()

    return render_template("admin.html", patients=patients)

# -------------------------------------------------
# Prediction
# -------------------------------------------------
@app.route("/predict", methods=["POST"])
def predict():

    patient_name = request.form.get("patient_name")
    age = request.form.get("age")
    gender = request.form.get("gender")
    smoking = request.form.get("smoking")

    file = request.files.get("scan")

    if not file:
        return "No file uploaded", 400

    img = tf.keras.preprocessing.image.load_img(BytesIO(file.read()), target_size=(224,224))

    img_array = tf.keras.preprocessing.image.img_to_array(img)

    img_array_norm = np.expand_dims(img_array, axis=0) / 255.0

    preds = model.predict(img_array_norm)[0]

    pred_index = int(np.argmax(preds))

    pred_label = class_labels[pred_index]

    confidence = float(np.max(preds) * 100)

    heatmap, _ = get_gradcam(img_array_norm, model)

    original = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    heatmap = cv2.resize(heatmap, (original.shape[1], original.shape[0]))

    coverage, stage = calculate_cancer_stage(heatmap)

    heatmap_uint8 = np.uint8(255 * heatmap)

    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

    gradcam = cv2.addWeighted(original, 0.6, heatmap_color, 0.4, 0)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    scan_file = f"scan_{timestamp}.png"

    gradcam_file = f"gradcam_{timestamp}.png"

    cv2.imwrite(os.path.join(UPLOAD_DIR, scan_file), original)

    cv2.imwrite(os.path.join(UPLOAD_DIR, gradcam_file), gradcam)

    conn = get_db()

    conn.execute(
        """
        INSERT INTO patients
        (patient_name,age,gender,smoking,scan_path,gradcam_path,prediction,confidence,stage)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            patient_name,
            age,
            gender,
            smoking,
            scan_file,
            gradcam_file,
            pred_label,
            confidence,
            stage
        ),
    )

    conn.commit()

    conn.close()

    return render_template(
        "results.html",
        patient_name=patient_name,
        prediction=pred_label,
        confidence=f"{confidence:.2f}%",
        coverage=f"{coverage}%",
        stage=stage,
        age=age,
        gender=gender,
        smoking=smoking
    )

# -------------------------------------------------
# Uploads
# -------------------------------------------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(UPLOAD_DIR, filename)

# -------------------------------------------------
# Delete Patient
# -------------------------------------------------
@app.route("/admin/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):

    conn = get_db()

    conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))

    conn.commit()

    conn.close()

    return redirect(url_for("admin"))

# -------------------------------------------------
# Run
# -------------------------------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)



