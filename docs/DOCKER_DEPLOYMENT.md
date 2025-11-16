# RVC2MQTT Docker Deployment Guide

## Overview
This guide covers deploying rvc2mqtt in a Docker container. The Docker deployment provides:
- Isolated runtime environment
- Easy updates and rollback
- Persistent logs and configuration
- Simplified dependency management
- Production-ready deployment

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- ESP32 SLCAN interface accessible on network (192.168.50.103:3333)
- MQTT broker accessible (Home Assistant Yellow at 192.168.50.77)
- Configuration file (rvc2mqtt.ini) properly configured

### 1. Clone Repository
```bash
git clone https://github.com/rv10guy/rvc2mqtt.git
cd rvc2mqtt
```

### 2. Configure
Edit `rvc2mqtt.ini` to match your environment:
```ini
[MQTT]
mqttBroker = 192.168.50.77    ; Your MQTT broker IP
mqttUser = hassio              ; Your MQTT username
mqttPass = hassio              ; Your MQTT password

[CAN]
CANport = 192.168.50.103:3333  ; Your ESP32 SLCAN TCP address
```

### 3. Create Log Directories
```bash
mkdir -p logs audit
```

### 4. Build and Run
```bash
docker-compose up -d
```

### 5. Verify Operation
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Check Home Assistant for auto-discovered entities
```

## Detailed Instructions

### Building the Docker Image

#### Option 1: Using Docker Compose (Recommended)
```bash
docker-compose build
```

#### Option 2: Using Docker Directly
```bash
docker build -t rvc2mqtt:latest .
```

### Running the Container

#### Using Docker Compose (Recommended)
```bash
# Start in detached mode
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop container
docker-compose down

# Restart container
docker-compose restart
```

#### Using Docker Directly
```bash
docker run -d \
  --name rvc2mqtt \
  --network host \
  --restart unless-stopped \
  -v $(pwd)/rvc2mqtt.ini:/app/rvc2mqtt.ini:ro \
  -v $(pwd)/mappings:/app/mappings:ro \
  -v $(pwd)/rvc-spec.yml:/app/rvc-spec.yml:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/audit:/app/audit \
  -e TZ=America/New_York \
  rvc2mqtt:latest
```

## Configuration

### Environment Variables
Configure via `docker-compose.yml`:
```yaml
environment:
  - TZ=America/New_York          # Your timezone
  # Optional overrides:
  # - DEBUG_LEVEL=1
  # - MQTT_BROKER=192.168.50.77
  # - MQTT_USER=hassio
  # - MQTT_PASS=hassio
```

### Volume Mounts
| Host Path | Container Path | Mode | Purpose |
|-----------|---------------|------|---------|
| `./rvc2mqtt.ini` | `/app/rvc2mqtt.ini` | ro | Configuration file |
| `./mappings` | `/app/mappings` | ro | Entity mapping files |
| `./rvc-spec.yml` | `/app/rvc-spec.yml` | ro | RV-C specification |
| `./logs` | `/app/logs` | rw | Application logs |
| `./audit` | `/app/audit` | rw | Command audit logs |

### Network Mode
The container uses **host network mode** by default for simplest configuration:
- No port mapping needed
- Direct access to ESP32 SLCAN TCP
- Direct access to MQTT broker
- Same network behavior as running natively

**Alternative: Bridge Mode** (for advanced users)
```yaml
network_mode: bridge
ports:
  - "1883:1883"  # If running MQTT broker in container
```

## Unraid Deployment

### Using Unraid Docker Manager

1. **Open Unraid Docker Tab**
   - Navigate to Docker tab in Unraid web UI
   - Click "Add Container"

2. **Container Configuration**
   ```
   Name: rvc2mqtt
   Repository: rvc2mqtt:latest
   Network Type: Host

   Volume Mappings:
   /mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini → /app/rvc2mqtt.ini (Read Only)
   /mnt/user/appdata/rvc2mqtt/mappings → /app/mappings (Read Only)
   /mnt/user/appdata/rvc2mqtt/rvc-spec.yml → /app/rvc-spec.yml (Read Only)
   /mnt/user/appdata/rvc2mqtt/logs → /app/logs (Read/Write)
   /mnt/user/appdata/rvc2mqtt/audit → /app/audit (Read/Write)

   Environment Variables:
   TZ = America/New_York

   Restart Policy: Unless Stopped
   ```

3. **Prepare Files**
   ```bash
   # SSH into Unraid server
   ssh root@unraid-ip

   # Create directories
   mkdir -p /mnt/user/appdata/rvc2mqtt/{logs,audit,mappings}

   # Copy files from development machine
   # (Use WinSCP, rsync, or git clone)
   ```

4. **Build Image on Unraid**
   ```bash
   cd /mnt/user/appdata/rvc2mqtt
   docker build -t rvc2mqtt:latest .
   ```

5. **Start Container**
   - Click "Apply" in Unraid Docker UI
   - Or use command line: `docker start rvc2mqtt`

### Using Docker Compose on Unraid
```bash
# SSH into Unraid
ssh root@unraid-ip

# Navigate to app directory
cd /mnt/user/appdata/rvc2mqtt

# Start with docker-compose
docker-compose up -d
```

## Maintenance

### Viewing Logs
```bash
# Docker Compose
docker-compose logs -f

# Docker directly
docker logs -f rvc2mqtt

# Application logs (on host)
tail -f logs/rvc2mqtt.log

# Audit logs (on host)
tail -f audit/command_audit.log
```

### Updating

#### Method 1: Rebuild from Source
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build
```

#### Method 2: Update Files Only (No Code Changes)
```bash
# Update configuration
vi rvc2mqtt.ini

# Update mappings
vi mappings/tiffin_default.yaml

# Restart to apply changes
docker-compose restart
```

### Backup
```bash
# Backup configuration and data
tar -czf rvc2mqtt-backup-$(date +%Y%m%d).tar.gz \
  rvc2mqtt.ini \
  mappings/ \
  logs/ \
  audit/

# Restore from backup
tar -xzf rvc2mqtt-backup-YYYYMMDD.tar.gz
```

### Rollback
```bash
# Stop current container
docker-compose down

# Checkout previous version
git log  # Find commit hash
git checkout <previous-commit>

# Rebuild and start
docker-compose up -d --build
```

## Troubleshooting

### Container Won't Start
```bash
# Check container status
docker-compose ps

# View full logs
docker-compose logs

# Check for errors in logs
docker-compose logs | grep -i error
```

**Common Issues:**
- **Permission denied**: Check volume mount permissions
  ```bash
  chmod 755 logs audit
  chmod 644 rvc2mqtt.ini
  ```
- **Port already in use**: Another process using network
  ```bash
  netstat -tulpn | grep LISTEN
  ```
- **Configuration error**: Check rvc2mqtt.ini syntax
  ```bash
  docker-compose config
  ```

### Cannot Connect to SLCAN
```bash
# Test ESP32 connectivity from container
docker exec -it rvc2mqtt ping 192.168.50.103

# Test SLCAN TCP port
docker exec -it rvc2mqtt nc -zv 192.168.50.103 3333

# Check if ESP32 is accessible from host
nc -zv 192.168.50.103 3333
```

**Fixes:**
- Ensure ESP32 is on same network
- Verify ESP32 IP address in configuration
- Check firewall rules
- Restart ESP32 SLCAN service

### Cannot Connect to MQTT
```bash
# Test MQTT connectivity from container
docker exec -it rvc2mqtt ping 192.168.50.77

# Check MQTT broker status (on HA Yellow)
# In Home Assistant: Settings → Add-ons → Mosquitto Broker → Logs
```

**Fixes:**
- Verify MQTT broker IP in configuration
- Check MQTT username/password
- Ensure MQTT broker allows remote connections
- Check Home Assistant Mosquitto configuration

### No Entities Appearing in Home Assistant
```bash
# Check if discovery messages are being published
docker-compose logs | grep "Publishing discovery"

# Check MQTT topics (from another terminal)
mosquitto_sub -h 192.168.50.77 -u hassio -P hassio -t "homeassistant/#" -v

# Verify mapping file is loaded
docker-compose logs | grep "Loading mapping"
```

**Fixes:**
- Check `discovery_enabled = 1` in rvc2mqtt.ini
- Verify mapping file exists and is valid YAML
- Restart Home Assistant to refresh MQTT integration
- Check Home Assistant MQTT integration is configured

### Container Crashes/Restarts
```bash
# Check recent logs
docker-compose logs --tail=100

# Check exit code
docker inspect rvc2mqtt | grep ExitCode

# Monitor resource usage
docker stats rvc2mqtt
```

**Fixes:**
- Check for Python exceptions in logs
- Verify all dependencies are installed
- Increase container memory limit if needed
- Check host system resources

## Performance Monitoring

### Container Statistics
```bash
# Real-time stats
docker stats rvc2mqtt

# Check health status
docker inspect rvc2mqtt | grep -A 5 Health
```

### Application Metrics
```bash
# CAN message processing
docker-compose logs | grep "messages processed"

# MQTT publish rate
docker-compose logs | grep "Published"

# Command latency
grep "latency" audit/command_audit.log
```

## Security Considerations

### File Permissions
```bash
# Recommended permissions
chmod 755 logs audit mappings
chmod 644 rvc2mqtt.ini rvc-spec.yml
chmod 644 mappings/*.yaml
```

### MQTT Credentials
Best practices for securing MQTT credentials:

1. **Use Environment Variables** (Recommended)
   ```yaml
   environment:
     - MQTT_USER=${MQTT_USER}
     - MQTT_PASS=${MQTT_PASS}
   ```

   Create `.env` file (add to .gitignore):
   ```
   MQTT_USER=hassio
   MQTT_PASS=your_secure_password
   ```

2. **Use Docker Secrets** (Most Secure)
   ```yaml
   secrets:
     mqtt_user:
       file: ./secrets/mqtt_user.txt
     mqtt_pass:
       file: ./secrets/mqtt_pass.txt
   ```

### Network Security
- Use host network mode only on trusted networks
- Consider VPN for remote access
- Enable MQTT authentication
- Use MQTT over TLS for encrypted communication

## Migration from VM/Native

### Pre-Migration Checklist
- [ ] Docker and Docker Compose installed on target system
- [ ] Configuration files backed up
- [ ] Log files archived
- [ ] MQTT broker and SLCAN accessible from Docker host
- [ ] Home Assistant MQTT integration configured

### Migration Steps
1. **Stop existing rvc2mqtt service**
   ```bash
   # On VM/native system
   pkill -f rvc2mqtt.py
   # Or: systemctl stop rvc2mqtt
   ```

2. **Copy files to Docker host**
   ```bash
   # On Docker host
   git clone https://github.com/rv10guy/rvc2mqtt.git
   cd rvc2mqtt

   # Copy your customized config
   scp vm-host:/path/to/rvc2mqtt.ini .
   scp -r vm-host:/path/to/mappings .
   ```

3. **Verify configuration**
   ```bash
   # Check all paths and IPs are correct
   cat rvc2mqtt.ini
   ```

4. **Start Docker container**
   ```bash
   mkdir -p logs audit
   docker-compose up -d
   ```

5. **Verify operation**
   ```bash
   docker-compose logs -f
   # Check Home Assistant for entities
   ```

6. **Monitor for 24-48 hours**
   - Check logs for errors
   - Verify all entities updating
   - Test commands from Home Assistant
   - Monitor resource usage

7. **Decommission old deployment**
   ```bash
   # Only after successful validation
   # On VM: systemctl disable rvc2mqtt
   # Or: remove VM
   ```

### Rollback Plan
If Docker deployment fails:
```bash
# Stop Docker container
docker-compose down

# Restart VM/native service
# On VM: systemctl start rvc2mqtt
# Or: python rvc2mqtt.py

# Debug Docker issues offline
```

## Updates and Upgrades

### Minor Updates (Configuration Only)
```bash
# Edit configuration
vi rvc2mqtt.ini

# Restart to apply
docker-compose restart

# No rebuild needed
```

### Major Updates (Code Changes)
```bash
# Pull latest code
git pull origin master

# Rebuild image
docker-compose build

# Stop and remove old container
docker-compose down

# Start new container
docker-compose up -d

# Verify operation
docker-compose logs -f
```

### Automatic Updates (Optional)
Use Watchtower for automatic container updates:
```yaml
# Add to docker-compose.yml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 86400 rvc2mqtt
```

## Advanced Configuration

### Custom Dockerfile Modifications
Example: Add additional Python packages
```dockerfile
# Add after pip install line in Dockerfile
RUN pip install --no-cache-dir numpy pandas
```

### Multi-Architecture Support
Build for different platforms:
```bash
# Build for ARM (Raspberry Pi)
docker buildx build --platform linux/arm64 -t rvc2mqtt:arm64 .

# Build for both AMD64 and ARM64
docker buildx build --platform linux/amd64,linux/arm64 -t rvc2mqtt:latest .
```

### Resource Limits
Add resource constraints to docker-compose.yml:
```yaml
services:
  rvc2mqtt:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
```

## Support and Help

### Useful Commands Reference
```bash
# Container Management
docker-compose up -d           # Start in background
docker-compose down            # Stop and remove
docker-compose restart         # Restart
docker-compose logs -f         # Follow logs
docker-compose ps              # List containers
docker-compose build           # Rebuild image

# Debugging
docker exec -it rvc2mqtt bash  # Interactive shell
docker inspect rvc2mqtt        # Container details
docker stats rvc2mqtt          # Resource usage

# Cleanup
docker system prune            # Remove unused images
docker volume prune            # Remove unused volumes
```

### Getting Help
- GitHub Issues: https://github.com/rv10guy/rvc2mqtt/issues
- Documentation: docs/ directory
- Logs: Check logs/ and audit/ directories

### Reporting Issues
Include in bug reports:
1. Docker version: `docker --version`
2. Docker Compose version: `docker-compose --version`
3. Container logs: `docker-compose logs`
4. Configuration (redact passwords): `cat rvc2mqtt.ini`
5. Platform: Unraid, Ubuntu, etc.

## Next Steps

After successful Docker deployment:
1. **Monitor stability** for 7+ days
2. **Benchmark performance** (latency, reliability)
3. **Plan Phase 3** (HA Add-on or ESP32 native)
4. **Consider HA Add-on** for tighter integration
5. **Explore ESP32 native solution** for standalone deployment

---

**Phase 2.5: Docker Deployment**
Last Updated: December 2025
Version: 2.5.0
