# Phase 2.5: Docker Deployment Plan

## Overview
Phase 2.5 focuses on deploying rvc2mqtt in a production-ready Docker container on Unraid server. This is an intermediate step between development (VM) and future deployment options (HA Add-on, ESP32).

## Goals
- Deploy rvc2mqtt in Docker on Unraid server
- Establish production deployment baseline
- Validate system reliability in production environment
- Prepare foundation for future HA Add-on migration

## Current Environment
- **HA Yellow**: Running HAOS with MQTT broker (192.168.50.77)
- **Unraid Server**: Running in RV, available for Docker containers
- **ESP32**: SLCAN TCP interface at 192.168.50.103:3333
- **Development**: Currently running on VM (temporary)

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      RV Network                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐     SLCAN TCP                         │
│  │   ESP32      │────────────────┐                      │
│  │ CAN Interface│    :3333       │                      │
│  └──────────────┘                │                      │
│                                   │                      │
│                                   ▼                      │
│                          ┌─────────────────┐            │
│                          │  Unraid Server  │            │
│                          │                 │            │
│                          │  ┌───────────┐  │            │
│                          │  │ rvc2mqtt  │  │            │
│                          │  │  Docker   │──┼────MQTT───┐│
│                          │  └───────────┘  │           ││
│                          └─────────────────┘           ││
│                                                         ││
│                          ┌─────────────────┐           ││
│                          │   HA Yellow     │           ││
│                          │                 │◄──────────┘│
│                          │  ┌───────────┐  │            │
│                          │  │HA + MQTT  │  │            │
│                          │  │  Broker   │  │            │
│                          │  └───────────┘  │            │
│                          └─────────────────┘            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Technical Tasks

### Task 1: Create Dockerfile
- [x] Design multi-stage build (if needed)
- [ ] Use Python 3.11 slim base image
- [ ] Copy all required Python files
- [ ] Install dependencies from requirements.txt
- [ ] Set appropriate working directory
- [ ] Configure entry point to run rvc2mqtt.py

### Task 2: Create docker-compose.yml
- [ ] Define service configuration
- [ ] Set network mode (host or bridge)
- [ ] Configure volume mounts for:
  - Configuration files (rvc2mqtt.ini)
  - Mappings directory
  - Logs directory
- [ ] Set environment variables (timezone, debug level)
- [ ] Configure restart policy

### Task 3: Create .dockerignore
- [ ] Exclude development files
- [ ] Exclude git files
- [ ] Exclude test files
- [ ] Exclude virtual environment
- [ ] Exclude logs

### Task 4: Create requirements.txt
- [ ] List all Python dependencies
- [ ] Pin versions for reproducibility
- [ ] Include:
  - paho-mqtt
  - PyYAML
  - python-can
  - Other dependencies

### Task 5: Configuration Management
- [ ] Document environment variables
- [ ] Create example configuration
- [ ] Plan for secrets management (MQTT credentials)
- [ ] Document volume mount structure

### Task 6: Documentation
- [ ] Create DOCKER_DEPLOYMENT.md guide
- [ ] Document Unraid-specific setup
- [ ] Document troubleshooting steps
- [ ] Create quick-start guide
- [ ] Document update procedure

### Task 7: Testing
- [ ] Build Docker image locally
- [ ] Test container startup
- [ ] Verify CAN bus connectivity
- [ ] Verify MQTT connectivity
- [ ] Test command processing
- [ ] Verify log persistence
- [ ] Test container restart behavior

### Task 8: Unraid Deployment
- [ ] Deploy to Unraid server
- [ ] Configure Unraid template (optional)
- [ ] Set up monitoring
- [ ] Configure auto-start
- [ ] Validate production operation

## Success Metrics
- Container builds without errors
- rvc2mqtt connects to SLCAN TCP interface
- rvc2mqtt connects to MQTT broker on HA Yellow
- All sensors appear in Home Assistant
- All commands work from Home Assistant
- Container survives restarts
- Logs persist across restarts
- System runs reliably for 7+ days

## File Structure
```
rvc2mqtt/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── rvc2mqtt.py
├── ha_discovery.py
├── rvc_commands.py
├── can_tx.py
├── command_handler.py
├── command_validator.py
├── audit_logger.py
├── rvc-spec.yml
├── rvc2mqtt.ini (example)
├── mappings/
│   └── tiffin_default.yaml
├── logs/ (mounted volume)
└── docs/
    ├── DOCKER_DEPLOYMENT.md (new)
    └── ...
```

## Configuration Considerations

### Network Mode Options
1. **Host Mode** (Recommended)
   - Simplest configuration
   - Direct access to ESP32 and MQTT
   - No port mapping needed

2. **Bridge Mode**
   - More isolation
   - Requires port exposure
   - May complicate SLCAN connection

### Volume Mounts
- **Configuration**: Read-only mount of rvc2mqtt.ini
- **Mappings**: Read-only mount of mappings directory
- **Logs**: Read-write mount for persistent logs
- **Optional**: Mount for audit logs

### Environment Variables
- `TZ`: Timezone (e.g., America/New_York)
- `DEBUG_LEVEL`: 0, 1, 2 for verbosity
- `MQTT_BROKER`: Override default from config
- `MQTT_USER`: Override default from config
- `MQTT_PASS`: Override default from config (use secrets!)

## Migration from VM
1. Stop VM-based rvc2mqtt
2. Build Docker image
3. Start Docker container
4. Verify Home Assistant connectivity
5. Monitor for 24 hours
6. Decommission VM

## Future Migration Path
Phase 2.5 → Phase 3 (HA Add-on):
- Docker container code can be reused
- Add add-on wrapper (config.json, run script)
- Minimal code changes required
- Smooth transition path

## Estimated Timeline
- Dockerfile creation: 1 hour
- docker-compose.yml: 30 minutes
- Documentation: 2 hours
- Testing: 2 hours
- Deployment: 1 hour
- Validation: 1 week (monitoring)

**Total active work**: ~7 hours

## Risks and Mitigation

### Risk: Network connectivity issues
**Mitigation**: Use host network mode, document troubleshooting

### Risk: Volume permission issues
**Mitigation**: Set appropriate user/group in Dockerfile

### Risk: Container fails to start
**Mitigation**: Comprehensive logging, health checks

### Risk: SLCAN connection drops
**Mitigation**: Implement retry logic (already exists)

### Risk: Lost configuration on updates
**Mitigation**: External volume mounts for all config

## Rollback Plan
If Docker deployment fails:
1. Stop Docker container
2. Restart VM-based deployment
3. Debug Docker issues offline
4. Retry deployment when fixed

## Next Steps After Phase 2.5
1. **Monitor production stability** (1-2 weeks)
2. **Gather performance metrics** (latency, reliability)
3. **Plan Phase 3** (HA Add-on or ESP32)
4. **Community feedback** (if sharing with others)

## Notes
- This is a deployment phase, not a feature phase
- Code remains unchanged from Phase 2
- Focus is on packaging and deployment
- Sets foundation for future deployment options
- Unraid provides excellent Docker management
- Can be adapted for other Docker hosts
