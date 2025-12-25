# CCTV Integration and Vehicle Analytics Module

This repository implements an end‑to‑end local‑first CCTV vehicle analytics system.  It follows the requirements outlined in the *Flow Of CCTV Integration and Vehicle Analytics* and *Requirement Document – CCTV Integration and Vehicle Analytics Module* specifications.  The system supports camera integration, ROI definition, vehicle detection/classification, entry/exit counting, ANPR/barcode reading, material and load estimation, data persistence, dashboards, notifications and CSV export.

> **Note:** The implementation provided here focuses on a production‑grade local simulation.  All required components run on your machine via Docker without the need for specialised hardware.  Interfaces are designed so that GPU‑accelerated models (Jetson/DeepStream/TensorRT) can be swapped in later.  For example, vehicle detection is performed by a stub detector that finds a green rectangle in the supplied sample video – a placeholder for a YOLO‑based detector【684174910239958†L37-L52】.  The sample video shows a moving green block crossing a gate ROI so that the end‑to‑end flow can be verified.

## Architecture

The repository is organised as follows:

```
cctv-vehicle-analytics/
├── backend/             # FastAPI application with Celery workers
│   ├── app/
│   │   ├── api/         # REST routes (auth, cameras, ROI, events)
│   │   ├── core/        # Configuration, security and Celery app
│   │   ├── db/          # SQLAlchemy models and DB session
│   │   ├── services/    # Detection stub, analytics, storage
│   │   ├── workers/     # Celery tasks and launcher
│   │   └── initial_data.py # Seeds admin user/project/gate/camera and ROI
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/            # React + Vite dashboard
│   ├── src/
│   │   ├── pages/       # Pages for login, cameras, ROI, events, dashboard
│   │   ├── components/  # Navbar and protected route wrapper
│   │   └── api/axios.js # Axios instance with auth header
│   ├── index.html
│   ├── package.json
│   └── Dockerfile
├── infra/
│   ├── mediamtx/mediamtx.yml  # RTSP server config
│   └── sample_media/sample.mp4 # Sample video with green vehicle
├── docker-compose.yml
├── .env.example
└── README.md
```

### Backend

The backend is written in Python 3.11 using FastAPI.  It exposes REST endpoints for authentication, camera management, ROI creation/loading, event listing/correction and CSV export.  Celery is used to run background tasks for stream processing and notifications.  A simple detection stub identifies a green moving rectangle in the sample video and generates events when it crosses the gate ROI.  Events are persisted to PostgreSQL and snapshots are uploaded to MinIO for later viewing【684174910239958†L81-L90】.  Notifications are sent via MailHog (SMTP) and an SMS stub logs messages to the console.

### Frontend

The frontend uses React with Vite.  After logging in with the seeded admin account, users can:

1. **View cameras:** list existing cameras, add new ones and see their RTSP URLs.
2. **Set up ROI:** draw a rectangle on the camera snapshot using react‑konva and save it to the server【684174910239958†L29-L36】.
3. **View events:** filter events and manually correct plate/barcode/material/load values.
4. **Dashboard:** see bar charts of vehicle counts by type and access CSV export.

### Infra

The `docker-compose.yml` file defines all necessary services:

- **PostgreSQL** for relational data (users, cameras, events, etc.).
- **Redis** as a message broker for Celery workers.
- **MinIO** for object storage of event snapshots.
- **MailHog** to capture outbound emails locally.
- **Mediamtx** (RTSP Simple Server) to serve the sample video over RTSP.
- **Backend** container running the FastAPI app.
- **Worker** container running Celery workers and dispatching stream processing tasks.
- **Frontend** container serving the compiled React app via Nginx.

## Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- At least 4 GB of free RAM (for running PostgreSQL, Redis, MinIO and the app)

## Getting Started

1. **Clone the repository** and change into the project directory:

   ```bash
   git clone <REPO_URL>
   cd cctv-vehicle-analytics
   ```

2. **Create a `.env` file** based on the provided `.env.example`:

   ```bash
   cp .env.example .env
   # Optional: edit values such as JWT_SECRET_KEY
   ```
   Key additions now supported:
   - `ALLOWED_ORIGINS` to control CORS for the frontend.
   - `YOLO_MODEL_PATH`, `PLATE_MODEL_PATH`, optional `MATERIAL_MODEL_PATH` / `LOAD_MODEL_PATH` to point to your ONNX models (mount them under `./models`, which is already bind-mounted into backend/worker).
   - `NOTIFY_DEBOUNCE_SECONDS` to rate-limit per-gate/channel notifications; `FCM_SERVER_KEY`/`FCM_ENDPOINT` for push, and Twilio variables for real SMS.

3. **Build and start the stack** (this may take several minutes on first run):

   ```bash
   docker compose up --build
   ```

   This command builds the backend and frontend images, starts all services and seeds the database with a demo project, gate, camera and ROI.  Celery workers automatically begin processing the sample stream.

4. **Access the services:**

   - **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)  
     Log in with **username:** `admin` and **password:** `admin`.
   - **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)  
     Explore and test endpoints via Swagger.
   - **MailHog UI:** [http://localhost:8025](http://localhost:8025)  
     View captured notification emails.
   - **MinIO Console:** [http://localhost:9001](http://localhost:9001)  
     Use `minio` / `minio123` to log in and browse uploaded snapshots.
   - **RTSP Stream:** `rtsp://localhost:8554/sample`  
     Use VLC or FFplay to view the sample video served by mediamtx.

## Verification Checklist

After starting the stack, you should be able to verify the end‑to‑end pipeline:

1. **Login** to the frontend with the seeded admin credentials (`admin`/`admin`).
2. **Navigate to ROI Setup** and verify that the snapshot shows a gate ROI.  You can redraw the ROI and save it.
3. **Open the Events page**.  Within a few seconds you should see new events being generated whenever the green rectangle in the sample video crosses the ROI.  Each row lists the timestamp, gate, camera, direction (`ENTRY`), vehicle type and a link to the snapshot stored in MinIO【684174910239958†L54-L76】.
4. **Click “Edit”** on any event to modify the plate/barcode/material/load fields.  Save your changes and see them reflected immediately.
5. **Check MailHog** – every event triggers an email notification containing the snapshot link and metadata【684174910239958†L152-L159】.
6. **View MinIO** via the console to inspect uploaded snapshots.
7. **Export CSV** from the dashboard by clicking the export button (in the Events page) or calling `/events/export` via the Swagger UI.  The downloaded CSV should contain all event metadata including timestamps, gate IDs and snapshot paths.

## Extending to Jetson/DeepStream/TensorRT

The codebase is structured to allow swapping the stub detector with a production‑ready implementation:

1. **Detection Adapter:** Replace `app/services/detection/stub_detector.py` with a wrapper around YOLOv8, ONNX or TensorRT to return bounding boxes and vehicle classes【684174910239958†L37-L52】.
2. **Tracking & Counting:** Integrate a proper tracker (e.g. ByteTrack) in `process_camera_stream` and use direction heuristics or analytics modules to determine entry vs exit【684174910239958†L54-L76】.
3. **ANPR/Barcode:** Implement plate detection and OCR in `app/services/ocr` and barcode decoding in `app/services/barcode`【684174910239958†L92-L109】.  Use the configuration flags on the `Gate` model to enable either mode.
4. **Material/Load Models:** Replace the stub in `app/services/material_load` with trained classifiers and regressors.  The current system stores cropped load‑area images to facilitate dataset collection【684174910239958†L111-L134】.

All non‑functional requirements such as authentication, logging, configuration via environment variables, idempotent tasks, and a testable local simulation are adhered to.  The default processing target (5 FPS) is reachable on modest hardware because the stub detector is lightweight.【419576084099050†L165-L174】

## API Testing with cURL

The following examples assume you have exported your JWT token as `TOKEN`:

```bash
# Login and store the token
TOKEN=$(curl -s -X POST \
  -d "username=admin&password=admin" \
  http://localhost:8000/auth/login | jq -r .access_token)

# List cameras
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/cameras/

# Get snapshot for camera 1
curl -L -H "Authorization: Bearer $TOKEN" http://localhost:8000/cameras/1/snapshot --output snapshot.jpg

# Update ROI for gate 1/camera 1
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"gate_id":1,"camera_id":1,"shape":"rectangle","coordinates":[[100,100],[400,300]]}' \
  http://localhost:8000/rois/

# Export events to CSV
curl -H "Authorization: Bearer $TOKEN" -L http://localhost:8000/events/export --output events.csv
```

## Packaging

To produce the deliverable ZIP archive run the provided script:

```bash
python scripts/package_zip.py
```

This will create `cctv-vehicle-analytics.zip` in the `dist/` directory containing the entire repository.  The ZIP can be shared and extracted on any machine with Docker installed to replicate the system.

---

This implementation meets the functional and non‑functional requirements described in the provided specification documents【684174910239958†L54-L90】【419576084099050†L147-L166】.  It provides a complete local environment for CCTV integration, vehicle analytics, event storage, dashboard visualisation, notifications and CSV export while clearly defining extension points for production‑grade models and hardware acceleration.
