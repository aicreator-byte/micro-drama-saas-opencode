# Micro Drama SaaS - Installation & Deployment Guide

## Quick Start (Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.12+ (for backend development)
- PostgreSQL 16+ (or use Docker)
- Redis 7+ (or use Docker)
- FFmpeg (for video processing)

### Using Docker Compose (Recommended)

1. Clone the repository and navigate to the opencode directory:
```bash
cd opencode
```

2. Copy the environment file and configure:
```bash
cp .env.example .env
# Edit .env with your values
```

3. Start all services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Manual Development Setup

#### Backend
```bash
cd app/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp ../.env.example .env
# Edit .env

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd app/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Production Deployment

### Environment Variables

Required production variables:
- `SECRET_KEY` - Strong random string (min 32 chars)
- `ENCRYPTION_KEY` - 32-character encryption key
- `POSTGRES_PASSWORD` - Secure database password
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `CORS_ORIGINS` - JSON array of allowed origins

### Docker Production Build

```bash
# Build images
docker-compose -f docker-compose.yml build

# Run in production mode
docker-compose -f docker-compose.yml up -d
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Project Structure

```
micro-drama-saas/
├── opencode/
│   ├── app/
│   │   ├── backend/          # FastAPI backend
│   │   │   ├── app/
│   │   │   │   ├── api/      # API routes
│   │   │   │   ├── core/     # Config, security, database
│   │   │   │   ├── models/   # SQLAlchemy models
│   │   │   │   ├── schemas/  # Pydantic schemas
│   │   │   │   └── main.py   # FastAPI app
│   │   │   ├── alembic/      # Database migrations
│   │   │   ├── requirements.txt
│   │   │   └── Dockerfile
│   │   └── frontend/         # Next.js frontend
│   │       ├── src/
│   │       │   ├── app/      # Next.js App Router pages
│   │       │   ├── components/
│   │       │   ├── lib/      # Utilities, API client, stores
│   │       │   └── types/
│   │       ├── package.json
│   │       └── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── hermes/                   # Hermes agent workspace
└── claude/                   # Claude agent workspace
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user
- `PUT /api/v1/auth/me` - Update current user
- `POST /api/v1/auth/logout` - Logout

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Series Bible
- `POST /api/v1/projects/{id}/series-bible` - Create series bible
- `GET /api/v1/projects/{id}/series-bible` - Get series bible
- `PUT /api/v1/projects/{id}/series-bible` - Update series bible
- `DELETE /api/v1/projects/{id}/series-bible` - Delete series bible

### Characters (max 6 per project)
- `POST /api/v1/projects/{id}/characters` - Create character
- `GET /api/v1/projects/{id}/characters` - List characters
- `GET /api/v1/projects/{id}/characters/{char_id}` - Get character
- `PUT /api/v1/projects/{id}/characters/{char_id}` - Update character
- `DELETE /api/v1/projects/{id}/characters/{char_id}` - Delete character

### Locations
- `POST /api/v1/projects/{id}/locations` - Create location
- `GET /api/v1/projects/{id}/locations` - List locations
- `GET /api/v1/projects/{id}/locations/{loc_id}` - Get location
- `PUT /api/v1/projects/{id}/locations/{loc_id}` - Update location
- `DELETE /api/v1/projects/{id}/locations/{loc_id}` - Delete location

### Episodes & Scenes
- `POST /api/v1/projects/{id}/episodes` - Create episode
- `GET /api/v1/projects/{id}/episodes` - List episodes
- `POST /api/v1/projects/{id}/episodes/{ep_id}/scenes` - Create scene
- `GET /api/v1/projects/{id}/episodes/{ep_id}/scenes` - List scenes
- `POST /api/v1/projects/{id}/episodes/{ep_id}/scenes/{sc_id}/shots` - Create shot

### Prompts
- `POST /api/v1/projects/{id}/prompts` - Create prompt
- `GET /api/v1/projects/{id}/prompts` - List prompts

### Google Accounts (max 20 per user)
- `POST /api/v1/google-accounts` - Create/connect account
- `POST /api/v1/google-accounts/connect` - Connect with session data
- `GET /api/v1/google-accounts` - List accounts
- `PUT /api/v1/google-accounts/{id}` - Update account
- `PUT /api/v1/google-accounts/{id}/session` - Update session
- `POST /api/v1/google-accounts/{id}/verify` - Verify account
- `DELETE /api/v1/google-accounts/{id}` - Disconnect account

### Flow Bridge
- `POST /api/v1/projects/{id}/flow-tasks` - Create task
- `GET /api/v1/projects/{id}/flow-tasks` - List tasks
- `POST /api/v1/projects/{id}/flow-assets` - Create asset
- `GET /api/v1/projects/{id}/flow-assets` - List assets

### Audit Logs (superuser only)
- `GET /api/v1/audit-logs` - List audit logs
- `GET /api/v1/audit-logs/{id}` - Get audit log

## Multi-Tenant Security

The application implements strict multi-tenant isolation:

1. **Project Ownership** - Every project belongs to a user (owner_id)
2. **Access Control** - All API routes verify project ownership before operations
3. **Data Isolation** - Users can only access their own projects, characters, locations, etc.
4. **Google Account Isolation** - Each user's Google accounts are isolated
5. **Audit Logging** - All sensitive operations are logged

## Testing

### Backend Tests
```bash
cd app/backend
pytest -v
```

### Frontend Tests
```bash
cd app/frontend
npm test
```

## Known Limitations (MVP)

1. **AI Integration** - Story/Script generation via LLMs not yet implemented
2. **Video Generation** - Direct video generation API integration pending
3. **Google Flow Automation** - Browser automation for Google Flow not implemented
4. **File Upload** - Asset upload to S3/local storage not fully implemented
5. **Real-time Updates** - WebSocket support for live collaboration not implemented
6. **Payment/Billing** - Subscription management not implemented
7. **Email Verification** - Email verification flow not implemented

## Future Development Recommendations

1. **AI Story Engine** - Integrate LLM for story/character/scene generation
2. **Video Pipeline** - Implement FFmpeg-based video assembly
3. **Google Flow Automation** - Playwright-based browser automation
4. **Asset Management** - S3-compatible storage with CDN
5. **Collaboration** - Real-time editing with WebRTC/WebSockets
6. **Billing** - Stripe integration for subscriptions
7. **Mobile App** - React Native / Flutter frontend
8. **Analytics** - Production metrics and cost tracking
9. **Templates** - Genre-specific project templates
10. **Export** - Multiple export formats (Final Draft, Fountain, etc.)

## License

MIT License - See LICENSE file for details.