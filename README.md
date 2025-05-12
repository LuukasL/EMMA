# Autonomous Defense Drone Control System

A specialized control system for autonomous defense drones, optimized for operation in Finnish terrain and climate conditions.

## Project Overview

This project develops a custom control interface for autonomous defense drones based on the ArduPilot framework. The system enables military operators to plan, execute and monitor autonomous patrol missions in challenging environments.

### Key Features

- Military-grade mission planning interface
- Autonomous patrol route generation
- Specialized for harsh Nordic climate operation
- Future: GPS-denied navigation using terrain recognition

## System Requirements

### Development Environment
- Python 3.8+
- PyQt6
- ArduPilot development environment (included as submodule)

### Deployment Environment
- Tablet device (7-9 inch) with minimum 1200×800 resolution
- Linux OS
- Connection hardware for drone communication


### Drone Configuration

*Documentation for configuring compatible drones will be added as the project progresses.*

## Project Structure

- `/UI` - User interface components
- `/mission` - Mission planning and execution logic
- `/communication` - ArduPilot integration and communication
- `/flight_control` - Enhanced flight control capabilities
- `/ardupilot` - ArduPilot submodule (do not modify directly)

## Development Status

Current development phase: **Initial Prototype**

- [x] Basic application structure
- [x] Mission control interface
- [ ] Map integration
- [ ] ArduPilot command translation
- [ ] Simulated mission testing
- [ ] Physical drone testing

## Roadmap

### Phase 1: MVP (Q2 2025) Before and during San Francisco trip
- Complete basic mission planning interface
- Implement GPS-based autonomous patrol capabilities
- Test with simulated environment (SITL)
- Initial field testing with physical drone

### Phase 2: Enhanced Capabilities (Q3 2025)
- Multiple drone coordination
- Advanced mission templates
- Performance optimization for cold weather
- Integration with military coordinate systems

### Phase 3: Advanced Navigation (Q4 2025)
- Computer vision-based navigation research
- Integration with Finnish terrain data
- GPS-denied operation capabilities
- Extended environmental operation range

## Military Use Considerations

This system is designed specifically for defense applications and contains features optimized for military use cases. Operation should comply with:
- Finnish military regulations
- NATO interoperability standards
- Relevant export control regulations

## Contributors

- Luukas Lohilahti - Lead Developer, CEO/CTO
- Touko Rautiainen- - Electronic Warfare Specialist, Designer

## License

*Proprietary - All rights reserved*

*ArduPilot is used under its respective license terms.*
