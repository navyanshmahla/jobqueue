import time
from datetime import datetime
from typing import List, Optional, Dict
from queue import PriorityQueue
from threading import Thread, Event, Lock
from dataclasses import dataclass
from .job_manager import Job, JobStatus, JobType
from .gpu_monitor import GPUType

@dataclass
class ScheduledJob:
    job: Job
    priority: int
    scheduled_time: Optional[datetime] = None
    
    def __lt__(self, other):
        if self.scheduled_time and other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        return self.priority > other.priority

class JobScheduler:
    def __init__(self, job_manager, execution_engine):
        self.job_manager = job_manager
        self.execution_engine = execution_engine
        self.queue = PriorityQueue()
        self.stop_event = Event()
        self.scheduler_thread = None
        self.running_jobs: Dict[str, Dict] = {}  # Track running jobs and their resource assignments
        self.resource_lock = Lock()  # Lock for thread-safe resource management
        
    def start(self):
        """Start the scheduler thread."""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.stop_event.clear()
            self.scheduler_thread = Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            
    def stop(self):
        """Stop the scheduler thread."""
        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join()
            
    def _run_scheduler(self):
        """Main scheduler loop."""
        while not self.stop_event.is_set():
            try:
                # Check for new jobs
                for job in self.job_manager.jobs.values():
                    if job.status == JobStatus.PENDING:
                        self._schedule_job(job)
                        
                # Process the queue
                self._process_queue()
                
                # Sleep for a short interval
                time.sleep(1)
                
            except Exception as e:
                print(f"Error in scheduler: {str(e)}")
                time.sleep(5)  # Wait before retrying
                
    def _schedule_job(self, job: Job):
        """Schedule a job based on its configuration."""
        if job.schedule_type == "queue":
            # For queue-based scheduling, add to priority queue
            scheduled_job = ScheduledJob(
                job=job,
                priority=job.priority
            )
            self.queue.put(scheduled_job)
            job.status = JobStatus.PENDING
            
        elif job.schedule_type == "time":
            # For time-based scheduling, check if it's time to run
            if job.start_time and datetime.now() >= job.start_time:
                scheduled_job = ScheduledJob(
                    job=job,
                    priority=job.priority,
                    scheduled_time=job.start_time
                )
                self.queue.put(scheduled_job)
                job.status = JobStatus.PENDING
                
    def _process_queue(self):
        """Process jobs in the queue, allowing parallel execution when possible."""
        # Get all pending jobs from queue
        pending_jobs = []
        while not self.queue.empty():
            scheduled_job = self.queue.get()
            if scheduled_job.job.status == JobStatus.PENDING:
                pending_jobs.append(scheduled_job)
        
        # Sort jobs by priority and scheduled time
        pending_jobs.sort(reverse=True)  # Higher priority first
        
        # Try to schedule each job
        for scheduled_job in pending_jobs:
            job = scheduled_job.job
            
            # Skip if job is no longer pending
            if job.status != JobStatus.PENDING:
                continue
            
            # Check if required resources are available
            if self._are_resources_available(job):
                # Run the job in a separate thread
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
                self.job_manager._save_jobs()
                
                # Track resource assignment
                with self.resource_lock:
                    self.running_jobs[job.name] = {
                        'job_type': job.job_type,
                        'gpu_ids': job.gpu_ids if job.job_type == JobType.GPU else None,
                        'gpu_memory_per_device': job.gpu_memory_per_device if job.job_type == JobType.GPU else None,
                        'start_time': datetime.now()
                    }
                
                # Run job in a separate thread
                thread = Thread(target=self._run_job_thread, args=(job,))
                thread.daemon = True
                thread.start()
            else:
                # Put the job back in the queue if resources aren't available
                self.queue.put(scheduled_job)
                
    def _are_resources_available(self, job: Job) -> bool:
        """Check if required resources are available."""
        with self.resource_lock:
            if job.job_type == JobType.CPU:
                # CPU jobs can always run in parallel
                return True
                
            elif job.job_type == JobType.GPU:
                try:
                    gpu_info = self.job_manager.monitor_gpu_usage()
                    
                    # Check if any of the requested GPUs are already assigned
                    for running_job in self.running_jobs.values():
                        if running_job['job_type'] == JobType.GPU:
                            if any(gpu_id in running_job['gpu_ids'] for gpu_id in job.gpu_ids):
                                return False
                    
                    # Check if there's enough memory on each requested GPU
                    for gpu_id in job.gpu_ids:
                        if gpu_id in gpu_info:
                            gpu = gpu_info[gpu_id]
                            
                            # Skip memory check for Apple GPUs (they don't provide memory info)
                            if gpu['type'] == GPUType.APPLE:
                                continue
                                
                            available_memory = gpu['memory_total'] - gpu['memory_used']
                            
                            # If there's not enough memory available, job can't run
                            if available_memory < job.gpu_memory_per_device:
                                return False
                                
                            # Also check GPU utilization
                            if gpu['gpu_utilization'] > 90:
                                return False
                    
                    return True
                    
                except Exception:
                    # If we can't check GPU usage, be conservative
                    return False
                    
            return False  # Unknown job type
            
    def _run_job_thread(self, job):
        """Run a job in a separate thread."""
        try:
            success = self.execution_engine.run_job(job)
            
            if success:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
            else:
                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    job.status = JobStatus.PENDING
                    self.queue.put(ScheduledJob(
                        job=job,
                        priority=job.priority
                    ))
                else:
                    job.status = JobStatus.FAILED
            
            # Clean up resource assignment
            with self.resource_lock:
                if job.name in self.running_jobs:
                    del self.running_jobs[job.name]
                    
            self.job_manager._save_jobs()
            
        except Exception as e:
            print(f"Error in job thread {job.name}: {str(e)}")
            job.status = JobStatus.FAILED
            self.job_manager._save_jobs() 