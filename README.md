# Invoice OCR Application

A FastAPI-based application for extracting invoice data using PaddleOCR with a modern web interface.

## Features

- **User Authentication**: Secure JWT-based registration and login
- **Document Upload**: Upload invoice images (JPEG, PNG, PDF)
- **OCR Processing**: Automatic invoice data extraction using PaddleOCR
- **Real-time Updates**: WebSocket support for real-time task status updates
- **Web Interface**: Clean, responsive Alpine.js SPA
- **Async Database**: SQLAlchemy async ORM for high-performance database operations
- **RESTful API**: Complete REST API with comprehensive endpoints

## Technology Stack

- **Backend**: FastAPI with async support
- **Database**: SQLAlchemy ORM (supports SQLite for dev, PostgreSQL for production)
- **OCR**: PaddleOCR for document processing
- **Authentication**: JWT tokens with bcrypt password hashing
- **Frontend**: Alpine.js SPA with modern CSS
- **Server**: Uvicorn ASGI server

## Project Structure

```
invoice-ocr-app/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .env                   # Environment variables (created from .env.example)
├── .gitignore            # Git ignore rules
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py       # JWT authentication endpoints
│   │   ├── documents.py  # Document upload/download endpoints
│   │   └── tasks.py      # OCR task management & WebSocket
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py     # Pydantic settings from .env
│   │   └── security.py   # Password hashing, JWT, auth dependencies
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py   # SQLAlchemy async setup
│   │   ├── models.py     # User, Document, ProcessingTask models
│   │   └── crud.py       # Database operations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_engine.py # PaddleOCR processing & field extraction
│   │   └── task_manager.py # In-memory task tracking
│   ├── static/
│   │   └── index.html    # Complete Alpine.js web interface
│   └── templates/        # Optional Jinja2 templates
├── uploads/
│   └── documents/        # Uploaded invoice files
└── models/              # PaddleOCR model cache
```

## Setup Instructions

### Prerequisites

- Python 3.9+
- pip or conda

### 1. Clone or Navigate to Project

```bash
cd invoice-ocr-app
```

### 2. Create Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update values if needed:

```bash
cp .env.example .env
```

Default `.env` configuration:
- Database: SQLite (suitable for development)
- JWT Secret: Change in production (minimum 32 characters)
- Debug: True (set to False in production)

### 5. Run the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload
```

The application will start at: **http://localhost:8000**

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/me` - Get current user info

### Documents
- `POST /documents/upload` - Upload invoice document
- `GET /documents/` - List user's documents
- `GET /documents/{document_id}` - Get document info
- `GET /documents/{document_id}/download` - Download document

### Tasks
- `POST /tasks/create` - Create new OCR processing task
- `GET /tasks/{task_id}` - Get task status
- `WebSocket /tasks/ws/{task_id}` - Real-time task status updates

### Health
- `GET /api/health` - Health check endpoint

## Using the Application

### 1. Register/Login
- Click the "Auth" tab
- Register a new account or login with existing credentials
- Save the JWT token (automatically stored in browser localStorage)

### 2. Upload Invoice
- Click the "Upload" tab
- Select an invoice image (JPEG, PNG, or PDF)
- Click "Upload"

### 3. Process Invoice
- Go to "Documents" tab
- Click "Process" on any document
- Automatic OCR processing starts

### 4. View Results
- Go to "Tasks" tab
- View extracted invoice data:
  - Vendor name
  - Invoice number
  - Invoice date
  - Total amount & currency
  - Confidence score

## Configuration

### Environment Variables

```env
# Database (SQLite for dev, PostgreSQL for prod)
DATABASE_URL=sqlite+aiosqlite:///./invoice_ocr.db
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/invoice_ocr_db

# JWT Configuration
SECRET_KEY=your-secret-key-change-this-in-production-min-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API
API_TITLE=Invoice OCR API
API_VERSION=0.1.0
DEBUG=True

# Server
HOST=0.0.0.0
PORT=8000

# File Upload
MAX_UPLOAD_SIZE=104857600  # 100MB
UPLOAD_DIRECTORY=uploads/documents

# OCR
OCR_MODEL_CACHE_DIR=models
```

## Database Setup

For PostgreSQL (production):

```bash
# Update DATABASE_URL in .env to:
DATABASE_URL=postgresql+asyncpg://user:password@localhost/invoice_ocr_db

# Create database
createdb invoice_ocr_db

# Update asyncpg in requirements.txt (already included)
```

For SQLite (default, development):

```bash
# Just ensure aiosqlite is installed (already in requirements.txt)
# Database file will be created automatically
```

## Performance Optimization

### For Production:

1. **Database**: Use PostgreSQL instead of SQLite
2. **Task Queue**: Upgrade from in-memory to Celery + Redis
3. **Caching**: Implement Redis for model caching
4. **Frontend**: Use a CDN for static files
5. **API**: Use environment-based configuration for CORS

### Recommended Changes:

```bash
pip install celery redis
```

Then modify `task_manager.py` and `tasks.py` routes to use Celery.

## Troubleshooting

### OCR Model Download Issues
- First run will download PaddleOCR models (~100MB)
- Models cached in `models/` directory
- Ensure stable internet connection for first initialization

### Database Locked (SQLite)
- SQLite has limited concurrency
- Use PostgreSQL for production/multi-user scenarios

### WebSocket Connection Issues
- Ensure firewall allows WebSocket connections
- Check browser console for errors
- Verify token is valid and not expired

## Development Tips

### Running Tests
```bash
pytest -v
```

### Database Migrations
```bash
# Using Alembic (optional setup)
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Enable Debug Mode
Set `DEBUG=True` in `.env` for detailed error messages and auto-reload.

## Security Considerations

- ⚠️ **Change JWT_SECRET_KEY** in production (minimum 32 characters)
- ⚠️ **Use HTTPS** in production
- ⚠️ **Implement rate limiting** for API endpoints
- ⚠️ **Validate file uploads** (already done for file type/size)
- ⚠️ **Use environment variables** for sensitive data (never hardcode)

## Future Enhancements

- [ ] Batch processing for multiple invoices
- [ ] Webhook notifications for completed tasks
- [ ] Advanced field extraction with ML models
- [ ] Invoice data validation rules
- [ ] Export results to Excel/PDF
- [ ] Audit logging and compliance features
- [ ] Multi-language OCR support
- [ ] Docker containerization
- [ ] CI/CD pipeline

## License

MIT

## Support

For issues or questions, please open an issue in the repository.
