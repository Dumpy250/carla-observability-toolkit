# CARLA Observability Toolkit
🚧 Work in progress

An observability and telemetry toolkit for the CARLA autonomous driving simulator.

This project adds structured logging, metrics collection, and experiment instrumentation to CARLA simulation runs. The goal is to make simulation experiments easier to analyze, reproduce, and visualize.

## Project Goals

The toolkit focuses on three main areas:

- **Simulation Telemetry**
  - Vehicle metrics (speed, acceleration, steering)
  - Event logging (collisions, run lifecycle events)
  - Sensor data summaries

- **Structured Logging**
  - JSON event logs
  - CSV metrics output
  - Time-series compatible data

- **Experiment Analysis**
  - Run metadata tracking
  - Dataset generation from simulation runs
  - Visualization through a lightweight dashboard

## Current Status

🚧 Work in progress

Current development includes:

- Metric bus architecture
- Event logging pipeline
- CSV metrics export
- Simulation run instrumentation
- Dashboard prototype


## Example Output

Example files produced during a simulation run:
metrics.csv
events.json
run_metadata.json


These datasets can be used to analyze vehicle behavior and replay simulation events.

## Roadmap

Planned features include:

- Real-time dashboard visualization
- Sensor data analysis tools
- Multi-run comparison
- Experiment reproducibility tools

## Tech Stack

- Python
- CARLA Simulator
- Pygame client
- JSON / CSV telemetry outputs

## Author

Cameron Basham 
Software Engineering Student  
Project developed as part of a CARLA simulation research project.
