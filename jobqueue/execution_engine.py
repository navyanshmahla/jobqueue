import os
import subprocess
import signal
import time
from typing import Dict, Optional
from datetime import datetime
import psutil
from rich.console import Console

class ExecutionEngine:
    def __init__(self, storage_path: str = "~/.jobqueue"):
        self.storage_path = os.path.expanduser(storage_path)
        self.console = Console()
        self.running_processes: Dict[str, subprocess.Popen] = {}
        
    def _setup_environment(self, job) -> str:
        """Set up the execution environment for a job."""
        if job.environment == "conda":
            if not job.conda_env:
                raise ValueError("conda_env must be specified for conda environment")
            return f"conda run -n {job.conda_env}"
        elif job.environment == "venv":
            # TODO: Implement venv activation
            return ""
        return ""
        
    def _prepare_command(self, job) -> str:
        """Prepare the command to run the training script."""
        env_setup = self._setup_environment(job)
        
        # Set CUDA_VISIBLE_DEVICES
        gpu_ids = ",".join(map(str, job.gpu_ids))
        cuda_devices = f"CUDA_VISIBLE_DEVICES={gpu_ids}"
        
        # Convert parameters to command line arguments
        params = []
        for key, value in job.parameters.items():
            if isinstance(value, bool):
                params.append(f"--{key}" if value else f"--no-{key}")
            else:
                params.append(f"--{key} {value}")
                
        # Construct the full command
        cmd = f"{cuda_devices} {env_setup} python {job.script} {' '.join(params)}"
        return cmd
        
    def _setup_logging(self, job_name: str) -> tuple:
        """Set up logging for the job."""
        log_file = os.path.join(self.storage_path, f"{job_name}.log")
        return open(log_file, 'w'), open(log_file, 'r')
        
    def run_job(self, job) -> bool:
        """Run a job and return whether it was successful."""
        try:
            cmd = self._prepare_command(job)
            stdout_file, stderr_file = self._setup_logging(job.name)
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=stdout_file,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            
            self.running_processes[job.name] = process
            
            # Wait for the process to complete
            try:
                process.wait(timeout=None)
                success = process.returncode == 0
            except subprocess.TimeoutExpired:
                self.terminate_job(job.name)
                success = False
            finally:
                stdout_file.close()
                stderr_file.close()
                
            return success
            
        except Exception as e:
            self.console.print(f"[red]Error running job {job.name}: {str(e)}[/red]")
            return False
            
    def terminate_job(self, job_name: str) -> bool:
        """Terminate a running job."""
        if job_name in self.running_processes:
            process = self.running_processes[job_name]
            try:
                # Send SIGTERM to the process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                return True
            except subprocess.TimeoutExpired:
                # If SIGTERM didn't work, try SIGKILL
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    return True
                except ProcessLookupError:
                    return False
            finally:
                del self.running_processes[job_name]
        return False
        
    def get_process_status(self, job_name: str) -> Optional[Dict]:
        """Get the current status of a running process."""
        if job_name not in self.running_processes:
            return None
            
        process = self.running_processes[job_name]
        try:
            proc = psutil.Process(process.pid)
            return {
                'pid': process.pid,
                'cpu_percent': proc.cpu_percent(),
                'memory_percent': proc.memory_percent(),
                'status': proc.status(),
                'create_time': datetime.fromtimestamp(proc.create_time()).isoformat()
            }
        except psutil.NoSuchProcess:
            return None 