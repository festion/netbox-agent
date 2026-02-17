Okay, I have created the `PROJECT_INDEX.md` file.
7

## Purpose
The `netbox-agent` project is designed to integrate various infrastructure data sources (such as Proxmox, TrueNAS, Home Assistant, and network scanners) with a Netbox instance. It collects data from these systems, processes it, and synchronizes it with Netbox, potentially orchestrated by a Master Control Program (MCP) server, to maintain an up-to-date and centralized inventory of infrastructure assets.

## Architecture
- **`src/netbox_agent.py`**: The main application entry point, orchestrating the overall agent operations.
- **`src/netbox/`**: Contains the Netbox API client (`client.py`), data models (`models.py`), and synchronization logic (`sync.py`) for interacting with the Netbox instance.
- **`src/data_sources/`**: A collection of modules (e.g., `proxmox.py`, `truenas.py`, `network_scanner.py`) responsible for gathering data from different infrastructure systems.
- **`src/mcp/`**: Modules for managing interactions with MCP servers, which might orchestrate data collection and synchronization across multiple agents.
- **`src/scheduler/scheduler.py`**: Manages the scheduling and execution of data collection and synchronization tasks.
- **`src/utils/`**: Provides common utilities such as logging (`logging.py`), configuration loading (`config.py`), and error handling (`error_handling.py`).
- **`config/`**: Stores various configuration files, including agent settings, data mapping rules, and MCP server configurations.
- **`api/`**: Likely contains a web API for external interaction or data exposure.
- **`dashboard/`**: Suggests a web-based user interface for monitoring or controlling the agent.

## Key Files
- `README.md`: Project overview and getting started guide.
- `requirements.txt`: Python dependencies for the agent.
- `Dockerfile`: Defines the Docker image for the agent.
- `docker-compose.yml`: Orchestrates the agent and its dependencies using Docker Compose.
- `pytest.ini`: Pytest configuration file.
- `src/netbox_agent.py`: Main Python application logic.
- `src/netbox/client.py`: Netbox API client implementation.
- `src/data_sources/manager.py`: Manages various data source integrations.
- `src/mcp/manager.py`: Manages MCP server interactions.
- `config/template-netbox-agent.json`: Template for the main agent configuration.
- `config/data-mappings.json`: Defines how collected data maps to Netbox models.
- `scripts/install.sh`: Installation script for the agent.
- `scripts/run-agent.sh`: Script to run the Netbox agent.
- `deploy-to-remote.sh`: Script for remote deployment.
- `.github/workflows/ci.yml`: GitHub Actions CI workflow definition.

## Dependencies
- **Python (Runtime)**: Dependencies are listed in `requirements.txt`.
- **Node.js/npm (API & Dashboard)**: Dependencies for the `api/` and `dashboard/` components are specified in their respective `package.json` files.
- **Docker/Docker Compose**: Used for containerization and orchestration as defined in `Dockerfile` and `docker-compose.yml`.

## Common Tasks
- **Build/Setup**:
  - `scripts/install.sh`: Run to install necessary components.
  - `docker-compose build`: Build Docker images.
- **Test**:
  - `pytest`: Run all Python tests (configured via `pytest.ini`).
  - Refer to `.github/workflows/ci.yml` for CI test commands.
- **Run/Deploy**:
  - `scripts/run-agent.sh`: Execute the Netbox agent directly.
  - `docker-compose up`: Start the agent and its services using Docker Compose.
  - `deploy-to-remote.sh`: Script for deploying the agent to a remote environment.
