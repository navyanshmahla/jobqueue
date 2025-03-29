import os
import time
import yaml
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import psutil
from rich.console import Console
from rich.table import Table
from .gpu_monitor import GPUMonitor, GPUType

class JobType(Enum):
    CPU = "cpu"
    GPU = "gpu"

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    name: str
    script: str
    environment: str
    schedule_type: str
    job_type: JobType
    priority: int = 1
    gpu_ids: Optional[List[int]] = None
    gpu_memory_per_device: Optional[float] = None
    conda_env: Optional[str] = None
    parameters: Optional[Dict] = None
    start_time: Optional[datetime] = None
    max_retries: int = 3
    retry_count: int = 0
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_dir: Optional[str] = None
    log_file: Optional[str] = None

    def __post_init__(self):
        if self.job_type == JobType.GPU:
            if not self.gpu_ids:
                raise ValueError("GPU jobs must specify gpu_ids")
            if not self.gpu_memory_per_device:
                raise ValueError("GPU jobs must specify gpu_memory_per_device")

class JobManager:
    def __init__(self, storage_path: str = "~/.jobqueue"):
        self.storage_path = os.path.expanduser(storage_path)
        self.jobs: Dict[str, Job] = {}
        self.console = Console()
        self.gpu_monitor = GPUMonitor()
        self._init_storage()
        
    def _init_storage(self):
        """Initialize storage directory and load existing jobs."""
        os.makedirs(self.storage_path, exist_ok=True)
        self._load_jobs()
            
    def _load_jobs(self):
        """Load jobs from storage."""
        jobs_file = os.path.join(self.storage_path, "jobs.json")
        if os.path.exists(jobs_file):
            with open(jobs_file, 'r') as f:
                jobs_data = json.load(f)
                for job_data in jobs_data:
                    job = Job(**job_data)
                    job.status = JobStatus(job_data['status'])
                    job.job_type = JobType(job_data['job_type'])
                    if job_data.get('started_at'):
                        job.started_at = datetime.fromisoformat(job_data['started_at'])
                    if job_data.get('completed_at'):
                        job.completed_at = datetime.fromisoformat(job_data['completed_at'])
                    self.jobs[job.name] = job
                    
    def _save_jobs(self):
        """Save jobs to storage."""
        jobs_file = os.path.join(self.storage_path, "jobs.json")
        jobs_data = []
        for job in self.jobs.values():
            job_dict = job.__dict__.copy()
            job_dict['status'] = job.status.value
            job_dict['job_type'] = job.job_type.value
            if job.started_at:
                job_dict['started_at'] = job.started_at.isoformat()
            if job.completed_at:
                job_dict['completed_at'] = job.completed_at.isoformat()
            jobs_data.append(job_dict)
            
        with open(jobs_file, 'w') as f:
            json.dump(jobs_data, f)
            
    def submit_job(self, config_path: str) -> str:
        """Submit a new job from configuration file."""
        with open(config_path, 'r') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
                
        # Convert job type string to enum
        job_type = JobType(config['job_type'])
        
        job = Job(
            name=config['name'],
            script=config['script'],
            environment=config['environment'],
            schedule_type=config['schedule']['type'],
            job_type=job_type,
            priority=config['schedule']['priority'],
            start_time=datetime.fromisoformat(config['schedule']['start_time']) if config['schedule'].get('start_time') else None,
            parameters=config['parameters']
        )
        
        self.jobs[job.name] = job
        self._save_jobs()
        return job.name
        
    def get_job_status(self, job_name: str) -> Optional[JobStatus]:
        """Get the status of a specific job."""
        job = self.jobs.get(job_name)
        return job.status if job else None
        
    def cancel_job(self, job_name: str) -> bool:
        """Cancel a running job."""
        job = self.jobs.get(job_name)
        if job and job.status == JobStatus.RUNNING:
            # TODO: Implement process termination
            job.status = JobStatus.CANCELLED
            self._save_jobs()
            return True
        return False
        
    def list_jobs(self) -> List[Dict]:
        """List all jobs with their status."""
        return [
            {
                'name': job.name,
                'type': job.job_type.value,
                'status': job.status.value,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'priority': job.priority,
                'gpu_ids': job.gpu_ids,
                'gpu_memory_per_device': job.gpu_memory_per_device
            }
            for job in self.jobs.values()
        ]
        
    def get_job_logs(self, job_name: str) -> Optional[str]:
        """Get logs for a specific job."""
        log_file = os.path.join(self.storage_path, f"{job_name}.log")
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                return f.read()
        return None
        
    def monitor_gpu_usage(self) -> Dict:
        """Monitor GPU usage across all devices."""
        return self.gpu_monitor.get_gpu_info() 