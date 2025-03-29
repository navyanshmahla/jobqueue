import click
import os
import yaml
import json
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from datetime import datetime, timedelta
from typing import Optional
from .job_manager import JobManager, JobType
from .execution_engine import ExecutionEngine
from .scheduler import JobScheduler

console = Console()

def create_job_manager():
    """Create and initialize the job manager."""
    job_manager = JobManager()
    execution_engine = ExecutionEngine()
    scheduler = JobScheduler(job_manager, execution_engine)
    scheduler.start()
    return job_manager, scheduler

@click.group()
def cli():
    """JobQueue CLI - Manage your deep learning jobs efficiently."""
    pass

@cli.command()
@click.argument('name')
@click.option('--type', '-t', type=click.Choice(['cpu', 'gpu']), default='gpu',
              help='Type of job (cpu or gpu)')
@click.option('--gpu-ids', '-g', help='Comma-separated list of GPU IDs to use')
@click.option('--gpu-memory', '-m', type=float, help='GPU memory required per device in GB')
@click.option('--conda-env', '-e', help='Conda environment name')
@click.option('--script', '-s', help='Path to the training script')
@click.option('--priority', '-p', type=int, default=1, help='Job priority (higher number = higher priority)')
@click.option('--schedule-type', '-st', type=click.Choice(['queue', 'time']), default='queue',
              help='Scheduling type (queue or time)')
@click.option('--start-time', '-st', help='Start time in ISO format (YYYY-MM-DD HH:MM:SS)')
@click.option('--output', '-o', help='Output file path for the template')
def create_template(name: str, type: str, gpu_ids: Optional[str], gpu_memory: Optional[float],
                   conda_env: Optional[str], script: Optional[str], priority: int,
                   schedule_type: str, start_time: Optional[str], output: Optional[str]):
    """Generate a job template with the specified parameters."""
    
    # Create template dictionary
    template = {
        'name': name,
        'job_type': type,
        'script': script or 'python train.py',  # Default script
        'environment': 'local',  # Default environment
        'conda_env': conda_env,
        'schedule': {
            'type': schedule_type,
            'priority': priority,
            'start_time': start_time or datetime.now().isoformat()
        },
        'parameters': {
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 100
        }
    }
    
    # Add GPU-specific parameters if it's a GPU job
    if type == 'gpu':
        if not gpu_ids:
            click.echo("Warning: GPU job specified but no GPU IDs provided.")
            return
        if not gpu_memory:
            click.echo("Warning: GPU job specified but no GPU memory requirement provided.")
            return
            
        template['gpu_ids'] = [int(id.strip()) for id in gpu_ids.split(',')]
        template['gpu_memory_per_device'] = gpu_memory
    
    # Generate output path if not provided
    if not output:
        output = f"{name}_job.yaml"
    
    # Write template to file
    with open(output, 'w') as f:
        yaml.dump(template, f, default_flow_style=False)
    
    click.echo(f"Job template created successfully: {output}")
    click.echo("\nTemplate contents:")
    click.echo(yaml.dump(template, default_flow_style=False))

@cli.command()
@click.argument('config_file')
def submit(config_file: str):
    """Submit a job using the specified configuration file."""
    if not os.path.exists(config_file):
        click.echo(f"Error: Configuration file {config_file} does not exist.")
        return
        
    job_manager = JobManager()
    try:
        job_name = job_manager.submit_job(config_file)
        click.echo(f"Job submitted successfully with name: {job_name}")
    except Exception as e:
        click.echo(f"Error submitting job: {str(e)}")

@cli.command()
def list():
    """List all jobs and their status."""
    job_manager = JobManager()
    jobs = job_manager.list_jobs()
    
    if not jobs:
        click.echo("No jobs found.")
        return
        
    # Create a table to display jobs
    table = Table(show_header=True, header_style="bold magenta")
    
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Priority")
    table.add_column("Created At")
    table.add_column("Started At")
    table.add_column("Completed At")
    
    for job in jobs:
        table.add_row(
            job['name'],
            job['type'],
            job['status'],
            str(job['priority']),
            job['created_at'],
            job['started_at'] or "Not started",
            job['completed_at'] or "Not completed"
        )
    
    console.print(table)

@cli.command()
@click.argument('job_name')
def status(job_name: str):
    """Get the status of a specific job."""
    job_manager = JobManager()
    status = job_manager.get_job_status(job_name)
    
    if status:
        click.echo(f"Job {job_name} status: {status.value}")
    else:
        click.echo(f"Job {job_name} not found.")

@cli.command()
@click.argument('job_name')
def cancel(job_name: str):
    """Cancel a running job."""
    job_manager = JobManager()
    if job_manager.cancel_job(job_name):
        click.echo(f"Job {job_name} cancelled successfully.")
    else:
        click.echo(f"Could not cancel job {job_name}. Job might not exist or not be running.")

@cli.command()
@click.argument('job_name')
def logs(job_name: str):
    """Get logs for a specific job."""
    job_manager = JobManager()
    logs = job_manager.get_job_logs(job_name)
    
    if logs:
        click.echo(logs)
    else:
        click.echo(f"No logs found for job {job_name}.")

@cli.command()
def monitor():
    """Monitor GPU usage and job status in real-time."""
    try:
        job_manager, _ = create_job_manager()
        
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        with Live(layout, refresh_per_second=1) as live:
            while True:
                # Update header
                layout["header"].update(Panel("JobQueue Monitor", style="bold blue"))
                
                # Update body with job status
                jobs = job_manager.list_jobs()
                job_table = Table(show_header=True, header_style="bold magenta")
                job_table.add_column("Name")
                job_table.add_column("Status")
                job_table.add_column("Created At")
                job_table.add_column("Started At")
                job_table.add_column("Completed At")
                job_table.add_column("Priority")
                
                for job in jobs:
                    job_table.add_row(
                        job['name'],
                        job['status'],
                        job['created_at'],
                        job['started_at'] or "N/A",
                        job['completed_at'] or "N/A",
                        str(job['priority'])
                    )
                
                layout["body"].update(job_table)
                
                # Update footer with GPU usage
                gpu_usage = job_manager.monitor_gpu_usage()
                gpu_table = Table(show_header=True, header_style="bold green")
                gpu_table.add_column("GPU ID")
                gpu_table.add_column("GPU Utilization")
                gpu_table.add_column("Memory Used")
                gpu_table.add_column("Memory Total")
                
                for gpu_id, usage in gpu_usage.items():
                    gpu_table.add_row(
                        str(gpu_id),
                        f"{usage['gpu_utilization']}%",
                        f"{usage['memory_used']:.1f}MB",
                        f"{usage['memory_total']:.1f}MB"
                    )
                
                layout["footer"].update(gpu_table)
                
                time.sleep(1)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error in monitor: {str(e)}[/red]")

if __name__ == '__main__':
    cli() 