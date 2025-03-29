# JobQueue

A powerful job queue manager for deep learning workloads that helps you automate and schedule your experiments.

## Features

- Queue-based job scheduling for sequential execution
- Time-based scheduling with cron-like syntax
- Priority queuing for urgent experiments
- Automatic GPU resource management
- Experiment configuration via YAML/JSON
- Comprehensive monitoring and logging
- CLI interface for easy interaction

## Installation

```bash
pip install jobqueue
```

## Quick Start

1. Create a job configuration file (e.g., `experiment.yaml`):

```yaml
name: "mnist_training"
script: "train.py"
environment: "conda"
conda_env: "dl_env"
gpu_ids: [0, 1]
schedule:
  type: "queue"  # or "time"
  priority: 1
  start_time: "2024-03-26 14:00:00"  # for time-based scheduling
parameters:
  batch_size: 32
  learning_rate: 0.001
  epochs: 100
```

2. Submit a job:

```bash
jobq submit experiment.yaml
```

3. Monitor jobs:

```bash
jobq status
```

4. View logs:

```bash
jobq logs mnist_training
```

## Job Configuration

Jobs can be configured using YAML or JSON files. Here's a complete example:

```yaml
name: "experiment_name"
script: "path/to/training_script.py"
environment: "conda"  # or "venv"
conda_env: "environment_name"  # if using conda
gpu_ids: [0, 1]  # specify GPU devices to use
schedule:
  type: "queue"  # or "time"
  priority: 1  # higher number = higher priority
  start_time: "2024-03-26 14:00:00"  # for time-based scheduling
parameters:
  # Your experiment parameters here
  batch_size: 32
  learning_rate: 0.001
  epochs: 100
```

## CLI Commands

- `jobq submit <config_file>`: Submit a new job
- `jobq status`: View status of all jobs
- `jobq logs <job_name>`: View logs for a specific job
- `jobq cancel <job_name>`: Cancel a running job
- `jobq list`: List all jobs in the queue
- `jobq monitor`: Real-time monitoring of GPU usage and job status

## License

This project is licensed under the MIT License - see the LICENSE file for details. 