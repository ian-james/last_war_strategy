# Last War Scheduler

A strategic planning tool for the Last War game, built with Streamlit. Optimize your gameplay by tracking Arms Race events, VS Duels, and special events with smart scheduling and timezone support.

## Features

- **Strategic Dashboard**: Real-time tactical overview with optimization recommendations
- **Arms Race Scheduler**: Manage and track 6 daily Arms Race rotation slots
- **Special Events Manager**: Configure recurring events with timezone support
- **Smart Overlaps**: Automatically detect double-value opportunities when Arms Race and VS Duel tasks align
- **Multi-timezone Support**: Display times in your local timezone with 12h/24h format options
- **Data Persistence**: All schedules saved to CSV files

## Quick Start

### Using Docker (Recommended)

```bash
# Build and start the application
make start

# Access at http://localhost:8501
```

### Manual Installation

```bash
# Install dependencies using UV
uv sync

# Run the application
uv run streamlit run src/app/main.py
```

## Docker Commands

### Basic Operations
```bash
make help       # Show all available commands
make build      # Build Docker image
make up         # Start container
make down       # Stop container
make restart    # Restart container
make logs       # View logs (follow mode)
make status     # Check container status
```

### Development
```bash
make dev        # Start with hot-reload enabled
make shell      # Access container shell
make logs-tail  # View recent logs
```

### Data Management
```bash
make backup     # Backup data directory
make restore    # Restore from latest backup
```

### Maintenance
```bash
make rebuild    # Clean rebuild from scratch
make clean      # Remove container and image
make prune      # Clean all Docker resources
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Theme (optional)
STREAMLIT_THEME_PRIMARY_COLOR=#1976d2
STREAMLIT_THEME_BACKGROUND_COLOR=#ffffff
STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR=#f0f2f6
STREAMLIT_THEME_TEXT_COLOR=#262730

# Data Directory
DATA_DIR=./data
```

### Custom Port

To run on a different port:

```bash
# Edit docker-compose.yml
ports:
  - "8080:8501"  # Change 8080 to your desired port
```

Or use environment variable:
```bash
PORT=8080 make up
```

## Project Structure

```
last_war_scheduler/
├── src/
│   └── app/
│       └── main.py                  # Main Streamlit application
├── data/                            # Persistent data (CSV files)
│   ├── arms_race_schedule.csv       # Arms Race rotation (6 slots/day)
│   ├── vs_duel_schedule.csv         # VS Duel daily events
│   ├── special_events.csv           # Recurring special events
│   ├── daily_task_templates.csv     # Task templates (N/R/SR/SSR/UR)
│   ├── active_daily_tasks.csv       # Currently active tasks
│   └── restore_*.csv                # Backup restore snapshots
├── .devcontainer/
│   └── devcontainer.json            # Dev container configuration
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.yml               # Container orchestration
├── docker-compose.dev.yml           # Development overrides (hot reload)
├── Makefile                         # Docker management commands
├── pyproject.toml                   # Python dependencies
├── .python-version                  # Python version pin
├── uv.lock                          # Locked dependencies
├── context.md                       # Project context notes
├── debug_templates.py               # Template debugging utility
├── test_active_slot.py              # Active slot calculation tests
├── test_daily_tasks.py              # Daily task tests
└── test_slot_calculation.py         # Time slot validation tests
```

## Development

### Local Development with Hot Reload

```bash
# Start in development mode
make dev

# Application will reload automatically when you edit files
```

### Running Tests

```bash
# In container
make shell
uv run pytest

# Or locally
uv run pytest
```

## Data Backup

Data is automatically persisted in the `./data` directory. Create backups:

```bash
make backup     # Creates timestamped backup in backups/
make restore    # Restores from latest backup
```

## Troubleshooting

### Container won't start
```bash
make logs       # Check logs for errors
make rebuild    # Rebuild from scratch
```

### Port already in use
```bash
# Check what's using port 8501
lsof -i :8501

# Or change port in docker-compose.yml
```

### Data not persisting
```bash
# Ensure data directory has correct permissions
chmod 755 data/
```

### Health check failing
```bash
make health     # Check container health status
docker inspect last_war_scheduler
```

## Requirements

- Docker and Docker Compose
- Make (optional, for convenience commands)
- Python 3.12+ (for local development)

## License

Add your license here

## Contributing

Add contribution guidelines here
