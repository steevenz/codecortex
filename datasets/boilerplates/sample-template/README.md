# FastAPI Boilerplate Template

A simple and clean FastAPI application template with basic CRUD operations.

## Features

- ✅ FastAPI with automatic API documentation
- ✅ Pydantic models for data validation
- ✅ Basic CRUD operations
- ✅ Health check endpoint
- ✅ In-memory storage (easily replaceable with database)
- ✅ Uvicorn ASGI server
- ✅ Development dependencies included

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python src/main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn src.main:app --reload
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /items` - Get all items
- `GET /items/{item_id}` - Get item by ID
- `POST /items` - Create new item
- `PUT /items/{item_id}` - Update item
- `DELETE /items/{item_id}` - Delete item

## Example Usage

### Create an item
```bash
curl -X POST "http://localhost:8000/items" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Laptop",
       "description": "Gaming laptop",
       "price": 999.99,
       "is_available": true
     }'
```

### Get all items
```bash
curl "http://localhost:8000/items"
```

## Development

### Code Formatting
```bash
black src/
isort src/
```

### Linting
```bash
flake8 src/
```

### Testing
```bash
pytest
```

## Next Steps

1. Replace in-memory storage with a proper database (PostgreSQL, MySQL, etc.)
2. Add authentication and authorization
3. Implement proper error handling and logging
4. Add more comprehensive tests
5. Set up Docker containerization
6. Configure environment variables

## License

This template is provided as-is for educational and development purposes.