# RVC2MQTT Product Roadmap

## Vision
Make RV systems as smart and accessible as smart homes - enabling any RV owner to monitor and control their RV through Home Assistant with zero configuration.

## Guiding Principles
1. **User Experience First** - Zero-config should be the default
2. **Backwards Compatible** - Don't break existing deployments
3. **Open Standards** - MQTT, Home Assistant, ESPHome
4. **Community Driven** - Open source, documented, extensible
5. **Security Conscious** - Validate inputs, audit commands, secure by default

---

## Phase 1: Home Assistant MQTT Discovery (Q1 2026)
**Goal:** Make sensors auto-populate in Home Assistant without manual configuration

### Features
- [ ] Implement HA MQTT Discovery protocol
- [ ] Auto-create sensors for all RV-C message types
- [ ] Device grouping (batteries, tanks, HVAC, lights, etc.)
- [ ] Proper device classes and units of measurement
- [ ] Entity customization via config file
- [ ] Birth/will messages for availability tracking

### Technical Tasks
- [ ] Research HA MQTT Discovery protocol
- [ ] Design topic schema for discovery vs state
- [ ] Map RV-C message types to HA device classes
- [ ] Implement discovery message publishing
- [ ] Add configuration for entity customization
- [ ] Document discovery message format
- [ ] Create example HA dashboards

### Success Metrics
- Zero MQTT sensor configuration required in HA
- All entities properly categorized with icons
- Device page shows all RV systems grouped logically

### Estimated Effort
- Development: 2-3 weeks
- Testing: 1 week
- Documentation: 1 week

---

## Phase 2: Bidirectional Communication (Q2 2026)
**Goal:** Enable Home Assistant to control RV systems via MQTT commands

### Features
- [ ] MQTT command subscription (HA → Python)
- [ ] CAN bus message transmission (Python → CAN)
- [ ] Support for lights (on/off/dimming)
- [ ] Support for HVAC controls (temp, mode, fan)
- [ ] Support for pumps and switches
- [ ] Command validation and sanitization
- [ ] Rate limiting and error handling
- [ ] Command audit logging

### Technical Tasks
- [ ] Uncomment and modernize can_tx() function
- [ ] Subscribe to HA command topics
- [ ] Implement command parser (JSON → CAN frames)
- [ ] Create RV-C command encoder
- [ ] Add command validation layer
- [ ] Implement rate limiting (prevent CAN flooding)
- [ ] Add security controls (allowlist/denylist)
- [ ] Create command logging system
- [ ] Document supported commands and format

### Success Metrics
- Can control lights from HA dashboard
- Can adjust HVAC from HA
- Commands execute within 100ms
- Zero invalid commands reach CAN bus
- Full audit trail of all commands

### Estimated Effort
- Development: 3-4 weeks
- Testing: 2 weeks
- Documentation: 1 week

---

## Phase 3: Architecture Enhancement (Q3 2026)
**Goal:** Evaluate and optimize the overall system architecture

### Research & Decisions
- [ ] Benchmark MQTT latency and reliability
- [ ] Evaluate ESPHome RV-C feasibility
- [ ] Research HA custom component approach
- [ ] Prototype ESP32-native solution
- [ ] Compare Modbus TCP viability
- [ ] User survey on preferred architecture

### Potential Outcomes
1. **Stay with MQTT** - Optimize current approach
2. **Add ESPHome Path** - Parallel ESP32 solution
3. **Build HA Component** - Native integration
4. **Hybrid Approach** - Support multiple methods

### Technical Exploration
- [ ] Build proof-of-concept ESPHome RV-C component
- [ ] Measure MQTT vs direct integration performance
- [ ] Evaluate maintenance burden of each approach
- [ ] Cost analysis (hardware, development time)
- [ ] Community feedback gathering

### Success Metrics
- Clear architectural decision with data backing
- Prototype demonstrates viability
- Community buy-in on direction

### Estimated Effort
- Research: 2 weeks
- Prototyping: 3-4 weeks
- Documentation: 1 week

---

## Phase 4: ESP32 Native Solution (Q4 2026 - Q1 2027)
**Goal:** Create a standalone ESP32-based RV-C to HA bridge using ESPHome

### Features
- [ ] ESPHome custom component for RV-C
- [ ] Direct HA integration (no MQTT required)
- [ ] Web-based configuration UI
- [ ] OTA firmware updates
- [ ] Support for common RV systems
- [ ] Manufacturer-specific profiles
- [ ] Fallback MQTT mode for compatibility

### Technical Tasks
- [ ] Develop ESPHome RV-C CAN component
- [ ] Implement RV-C protocol parser in C++
- [ ] Create device type abstractions (sensor, binary_sensor, climate, etc.)
- [ ] Build configuration schema for YAML
- [ ] Implement manufacturer profiles (Tiffin, Newmar, etc.)
- [ ] Create web UI for setup wizard
- [ ] Add diagnostic tools and logging
- [ ] Design PCB for production hardware
- [ ] Write comprehensive documentation

### Success Metrics
- Flash ESP32, plug into CAN bus, auto-discovered in HA
- Sub-second response time for commands
- OTA updates work reliably
- Supports 90%+ of common RV systems

### Estimated Effort
- Development: 8-12 weeks
- Testing: 4 weeks
- Documentation: 2 weeks
- Hardware design: 4 weeks

---

## Phase 5: Multi-Manufacturer Support (Q2 2027)
**Goal:** Support RVs from multiple manufacturers, not just Tiffin

### Features
- [ ] Pluggable manufacturer profiles
- [ ] Auto-detection of RV manufacturer
- [ ] Custom DGN definitions per manufacturer
- [ ] Entity mapping configurator
- [ ] Community contribution framework
- [ ] Profile validation and testing tools

### Technical Tasks
- [ ] Refactor custom processing into profiles
- [ ] Create profile schema and loader
- [ ] Build profile editor/generator tool
- [ ] Add auto-detection logic (VIN, specific DGNs)
- [ ] Document profile creation process
- [ ] Create profile contribution guidelines
- [ ] Build profile testing framework

### Success Metrics
- Support 5+ major RV manufacturers
- Community contributes 3+ profiles
- Profile installation is single-click

### Estimated Effort
- Development: 6 weeks
- Testing: 3 weeks
- Documentation: 2 weeks

---

## Phase 6: Production Hardware (Q3-Q4 2027)
**Goal:** Create a commercial-grade plug-and-play hardware product

### Features
- [ ] Custom PCB with ESP32 + CAN transceiver
- [ ] Enclosure design (RV-appropriate)
- [ ] Pre-flashed firmware
- [ ] LED status indicators
- [ ] Push-button setup mode
- [ ] Power protection circuitry
- [ ] Certification (CE, FCC if needed)

### Technical Tasks
- [ ] PCB design and layout
- [ ] Component selection and sourcing
- [ ] Enclosure 3D design and fabrication
- [ ] Firmware factory programming
- [ ] Quality assurance testing
- [ ] Manufacturing partner selection
- [ ] Fulfillment and distribution setup
- [ ] Create product website
- [ ] Build order and support system

### Success Metrics
- Unit cost under $50
- 99%+ success rate on first connection
- Less than 1% RMA rate
- 4.5+ star average review

### Estimated Effort
- Hardware: 12 weeks
- Manufacturing setup: 8 weeks
- Website/commerce: 4 weeks
- Initial production run: 6 weeks

---

## Future Enhancements (2028+)

### Advanced Features
- [ ] Cloud integration for remote monitoring
- [ ] Mobile app (iOS/Android)
- [ ] Voice control (Alexa, Google Assistant)
- [ ] Predictive maintenance alerts
- [ ] Energy usage analytics
- [ ] Multi-RV fleet management
- [ ] Integration with campground reservation systems
- [ ] Weather-based automation

### Commercial Opportunities
- [ ] RV manufacturer partnerships
- [ ] Dealer installation program
- [ ] Subscription service (cloud features)
- [ ] Professional installation network
- [ ] White-label solutions

---

## Risk Mitigation

### Technical Risks
- **RV-C spec changes** - Monitor RVIA updates, maintain flexibility
- **HA breaking changes** - Follow HA dev closely, test beta releases
- **Hardware reliability** - Extensive testing, quality components
- **CAN bus interference** - Proper electrical isolation, filtering

### Business Risks
- **Market size** - Start open-source, validate before commercialization
- **Competition** - Focus on UX and ease-of-use differentiator
- **Support burden** - Build strong documentation, community support
- **Regulatory** - Ensure compliance before commercial launch

### Mitigation Strategies
1. Keep core open-source to ensure community longevity
2. Modular design allows pivoting between architectures
3. Start with Python to validate before ESP32 investment
4. Build community before building product
5. Partner with established RV tech companies

---

## Success Criteria

### Short-term (6 months)
- 100+ active users
- HA MQTT Discovery working reliably
- Bidirectional control functional
- Active GitHub community (issues, PRs, discussions)

### Medium-term (12-18 months)
- 500+ active users
- ESPHome component available
- Support for 3+ RV manufacturers
- Featured in HA community showcases

### Long-term (24+ months)
- 2000+ active users
- Commercial hardware product launched
- Profitable or sustainable via sponsorship
- Industry recognition (RV shows, HA conference)

---

## Open Questions

1. **Licensing**: Keep MIT or move to GPL for hardware protection?
2. **Governance**: Single maintainer or form a team/organization?
3. **Funding**: Donations, Patreon, commercial sales, or VC-backed?
4. **Brand**: Keep "rvc2mqtt" or rebrand for broader vision?
5. **Scope**: RV-only or expand to marine, industrial vehicles?

---

## Getting Started

The next immediate step is **Phase 1: HA MQTT Discovery**. This provides:
- Immediate value to existing users
- Validates the product-market fit
- Minimal risk (backwards compatible)
- Foundation for all future phases

**Recommended First Task:** Research HA MQTT Discovery protocol and design the topic schema.
