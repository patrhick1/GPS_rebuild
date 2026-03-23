# GPS Assessment Platform

A complete rebuild of the GPS (Gift, Passion, Story) assessment platform for Disciples Made, Inc.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python) |
| Frontend | React + Vite + TypeScript |
| Database | PostgreSQL |
| Hosting | Render |
| Billing | Stripe |
| Email | Resend |

## Project Structure

```
GPS Rebuild/
├── api/                    # FastAPI backend
│   ├── alembic/           # Database migrations
│   ├── app/
│   │   ├── core/          # Config, database, security
│   │   ├── dependencies/  # FastAPI dependencies
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # API route handlers
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   ├── tests/             # Test suite
│   ├── alembic.ini        # Alembic configuration
│   └── requirements.txt   # Python dependencies
├── web/                    # React frontend
│   ├── src/               # Source code
│   ├── public/            # Static assets
│   └── package.json       # Node dependencies
├── render.yaml            # Render deployment config
├── .gitignore
└── README.md
```

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL (local or cloud)

### Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd api
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the development server
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000
Docs at http://localhost:8000/docs

### Frontend Setup

```bash
cd web
npm install
npm run dev
```

The frontend will be available at http://localhost:5173

### Database Migrations

```bash
cd api

# Create a new migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Environment Variables

### Backend (.env)

```env
SECRET_KEY=your-super-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/gps_db
STRIPE_SECRET_KEY=sk_test_...
RESEND_API_KEY=re_...
FRONTEND_URL=http://localhost:5173
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
```

## Deployment

This project is configured for deployment on Render. See `render.yaml` for service configuration.

## Development Phases

1. **Phase 0: Prerequisites** - Infrastructure setup (current)
2. **Phase 1: Auth + Database Schema + User Registration** - Core authentication
3. **Phase 2: GPS Assessment Engine** - Assessment logic and scoring
4. **Phase 3: Personal Dashboard + History** - User-facing features
5. **Phase 4: Church Admin Dashboard** - Admin tooling
6. **Phase 5: Master Admin + Audit** - System administration
7. **Phase 6: Stripe Billing Integration** - Payments
8. **Phase 7: Data Migration + MyImpact** - Legacy data migration
9. **Phase 8: Cutover + Handoff** - Production launch

## License

Private - Disciples Made, Inc.
