# Docker Guide for Last War Scheduler

Complete guide for running and managing the Last War Scheduler with Docker.

## Table of Contents
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Environment Configuration](#environment-configuration)
- [Docker Commands](#docker-commands)
- [Development Workflow](#development-workflow)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Quick Start

### First Time Setup

```bash
# 1. Clone the repository (if needed)
git clone <repository-url>
cd last_war_scheduler

# 2. Setup environment variables
make env-setup

# 3. Build and start
make start

# 4. Access the application
# Open http://localhost:8501 in your browser
```

### Daily Usage

```bash
make up      # Start the application
make down    # Stop the application
make logs    # View logs
```

## Architecture

### Multi-Stage Docker Build

The Dockerfile uses a multi-stage build for optimization:

**Stage 1 - Builder:**
- Installs build dependencies
- Compiles Python packages
- Creates optimized virtual environment

**Stage 2 - Runtime:**
- Minimal base image
- Only runtime dependencies
- Non-root user for security
- Smaller final image size (~300MB vs ~800MB)

### Security Features

- **Non-root user**: Application runs as `appuser` (UID 1000)
- **Minimal dependencies**: Only essential packages in runtime
- **Health checks**: Automatic container health monitoring
- **Environment isolation**: Secrets managed via environment variables

### Data Persistence

Data is persisted in the `./data` directory:
- `last_standing_schedule.csv` - Arms Race schedules
- `special_events.csv` - Special event configurations
- Mounted as volume for persistence across container restarts

## Environment Configuration

### Creating Environment File

```bash
# From example template
make env-setup

# Or manually
cp .env.example .env
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_SERVER_PORT` | 8501 | Application port |
| `STREAMLIT_SERVER_ADDRESS` | 0.0.0.0 | Bind address |
| `STREAMLIT_SERVER_ENABLE_CORS` | false | CORS setting |
| `STREAMLIT_SERVER_HEADLESS` | true | Headless mode |
| `DATA_DIR` | ./data | Data directory path |

### Custom Theme Configuration

Add to `.env` file:

```env
STREAMLIT_THEME_PRIMARY_COLOR=#1976d2
STREAMLIT_THEME_BACKGROUND_COLOR=#ffffff
STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR=#f0f2f6
STREAMLIT_THEME_TEXT_COLOR=#262730
STREAMLIT_THEME_FONT=sans serif
```

### Checking Configuration

```bash
make env-check    # View current settings
make env-show     # View container environment
```

## Docker Commands

### Basic Operations

```bash
make help         # Show all commands
make build        # Build Docker image
make up           # Start container (detached)
make down         # Stop and remove container
make restart      # Restart container
make status       # Show container status
make health       # Check health status
```

### Viewing Logs

```bash
make logs         # Follow logs in real-time
make logs-tail    # Show last 100 lines
```

### Accessing Container

```bash
make shell        # Open bash shell in container

# Once inside:
ls -la           # View files
env              # View environment
pytest           # Run tests
```

### Image Management

```bash
make size         # Show image size
make rebuild      # Clean rebuild
make clean        # Remove image and container
make prune        # Clean all Docker resources
```

## Development Workflow

### Development Mode (Hot Reload)

```bash
# Start with auto-reload
make dev

# Or manually with dev compose
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Edit files in src/app/
# Changes automatically reload
```

### Running Tests

```bash
# In container
make shell
pytest

# Or directly
docker-compose exec last_war_scheduler pytest
```

### Debugging

```bash
# View logs with debug level
docker-compose logs -f --tail=100

# Check environment
make env-show

# Inspect container
docker inspect last_war_scheduler

# Check resource usage
docker stats last_war_scheduler
```

## Production Deployment

### Pre-deployment Checklist

- [ ] Review and update `.env` file
- [ ] Set appropriate port in `docker-compose.yml`
- [ ] Ensure `data/` directory has correct permissions
- [ ] Setup backup strategy
- [ ] Configure firewall rules
- [ ] Setup monitoring/alerting

### Building for Production

```bash
# Build optimized image
DOCKER_BUILDKIT=1 docker-compose build --no-cache

# Start in production mode
make prod

# Verify health
make health
```

### Custom Port Deployment

```bash
# Option 1: Environment variable
PORT=8080 make up

# Option 2: Interactive
make run-port

# Option 3: Edit docker-compose.yml
# Change ports: "8080:8501"
```

### Reverse Proxy Setup

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name scheduler.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Data Management

### Backup Strategy

```bash
# Create backup
make backup

# Backups stored in: backups/data-backup-YYYYMMDD-HHMMSS.tar.gz
```

### Restore Data

```bash
# Restore from latest backup
make restore

# Or manually
tar -xzf backups/data-backup-20260130-120000.tar.gz
```

### Manual Backup

```bash
# Backup specific files
cp data/last_standing_schedule.csv data/last_standing_schedule.csv.bak

# Full directory backup
tar -czf data-backup.tar.gz data/
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
make logs

# Rebuild from scratch
make rebuild

# Check port conflicts
lsof -i :8501
```

### Permission Errors

```bash
# Fix data directory permissions
chmod 755 data/
chown -R $(id -u):$(id -g) data/

# Or with container user
sudo chown -R 1000:1000 data/
```

### Health Check Failing

```bash
# Check health status
make health

# View detailed health logs
docker inspect --format='{{json .State.Health}}' last_war_scheduler | jq

# Check if port is accessible
curl http://localhost:8501/_stcore/health
```

### Port Already in Use

```bash
# Find process using port 8501
lsof -i :8501
sudo netstat -tulpn | grep 8501

# Kill process or use different port
PORT=8080 make up
```

### Data Not Persisting

```bash
# Check volume mount
docker inspect last_war_scheduler | jq '.[0].Mounts'

# Verify data directory
ls -la data/

# Ensure proper permissions
chmod 755 data/
```

### Image Build Failures

```bash
# Clear build cache
docker builder prune

# Rebuild without cache
docker-compose build --no-cache

# Check disk space
docker system df
df -h
```

### Memory Issues

```bash
# Check resource usage
docker stats last_war_scheduler

# Limit memory in docker-compose.yml
services:
  last-war-scheduler:
    deploy:
      resources:
        limits:
          memory: 512M
```

### Network Issues

```bash
# Check network
docker network ls
docker network inspect last-war-network

# Restart Docker daemon
sudo systemctl restart docker
```

## Performance Optimization

### Image Size Reduction

Current optimizations:
- Multi-stage build: ~60% size reduction
- Minimal base image (python:3.12-slim)
- No dev dependencies in production
- Cleaned apt cache

Check image size:
```bash
make size
```

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  last-war-scheduler:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          memory: 256M
```

### Build Cache

Enable BuildKit for faster builds:

```bash
export DOCKER_BUILDKIT=1
docker-compose build
```

## Monitoring and Logs

### Container Health

```bash
# Health status
make health

# Detailed health info
docker inspect --format='{{json .State.Health}}' last_war_scheduler | jq
```

### Resource Monitoring

```bash
# Real-time stats
docker stats last_war_scheduler

# Historical resource usage
docker stats --no-stream
```

### Log Management

```bash
# View logs
make logs

# Save logs to file
docker-compose logs > logs.txt

# Configure log rotation in docker-compose.yml
services:
  last-war-scheduler:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Advanced Usage

### Running Multiple Instances

```bash
# Copy project directory
cp -r last_war_scheduler last_war_scheduler_2

cd last_war_scheduler_2

# Use different port
PORT=8502 make up
```

### Docker Compose Profiles

Create profiles for different environments:

```yaml
services:
  last-war-scheduler:
    profiles: ["prod"]

  last-war-scheduler-dev:
    profiles: ["dev"]
    extends: last-war-scheduler
    volumes:
      - ./src:/app/src
```

Usage:
```bash
docker-compose --profile prod up
docker-compose --profile dev up
```

## Maintenance

### Regular Maintenance Tasks

```bash
# Weekly
make backup        # Backup data
make prune         # Clean unused resources

# Monthly
make rebuild       # Fresh rebuild
docker system prune -a --volumes  # Deep clean
```

### Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
make rebuild
make up
```

## Support

For issues or questions:
- Check logs: `make logs`
- Review status: `make status`
- Inspect health: `make health`
- Open issue on GitHub

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Project Repository](https://github.com/your-repo)
