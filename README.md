# Travel Agent SaaS Platform
**CMPE 131 — Scenario #7: The Family Vacationist**

Multi-tenant travel booking platform. Supports family-friendly hotel search, flight search, attractions/theme park filtering, and booking management.

---

## Requirements

- Python 3.12+
- Docker Desktop (optional, for Docker setup)

---

## Option 1: Run with Docker (Recommended)

**1. Start Docker Desktop**, then run:

```bash
docker compose up --build
```

The server will be running at `http://localhost:8000`.

To stop it:
```bash
docker compose down
```

---

## Option 2: Run Locally (without Docker)

**1. Navigate to the backend folder:**
```bash
cd backend
```

**2. Create and activate a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Start the server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be running at `http://localhost:8000`.

---

## API Documentation (Swagger UI)

Once the server is running, open your browser and go to:

```
http://localhost:8000/docs
```

This shows all available endpoints with the ability to test them directly.

---

## Environment Variables

The `.env` file is located at `backend/.env` and contains:

| Variable | Description |
|---|---|
| `RAPIDAPI_KEY` | RapidAPI key for Booking.com |
| `DATABASE_URL` | SQLite DB path (default: `sqlite:///./travel_saas.db`) |
| `SECRET_KEY` | Secret key used to sign JWT tokens |

---

## API Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/api/v1/auth/agency` | Register a new travel agency (tenant) | No |
| POST | `/api/v1/auth/signup` | Register a new user | No |
| POST | `/api/v1/auth/login` | Login and receive JWT token | No |
| GET | `/api/v1/hotels/search` | Search hotels (pool, occupancy, budget filters) | No |
| GET | `/api/v1/flights/search` | Search flights (multi-passenger) | No |
| GET | `/api/v1/attractions/search` | Search attractions / theme parks | No |
| POST | `/api/v1/bookings/` | Create a booking (Book Now) | Yes |
| GET | `/api/v1/bookings/{booking_id}` | Get booking details | Yes |
| GET | `/api/v1/bookings/user/{user_id}` | Get all bookings for a user (dashboard) | Yes |
| PATCH | `/api/v1/bookings/{booking_id}/status` | Update booking status | Yes |
| PATCH | `/api/v1/bookings/{booking_id}/cancel` | Cancel a booking | Yes |

Endpoints marked **Yes** require a `Bearer` token in the `Authorization` header. Get the token from `/login` or `/signup`.

---

## Project Structure

```
SWE1Proj/
├── docker-compose.yml
├── README.md
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── .env
    ├── main.py
    ├── database.py
    ├── models.py
    ├── schemas.py
    ├── middleware/
    │   └── tenant.py
    ├── services/
    │   └── rapidapi.py
    └── routers/
        ├── auth.py
        ├── hotels.py
        ├── flights.py
        ├── attractions.py
        └── bookings.py
```

---

## Group Members
- Ekueba Joyce Eslie Siaka
- Asmita Dulla
- Sandra Paez Olivarez
- Charlynn Nguyen
- Hugh Nguyen
