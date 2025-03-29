import platform
import subprocess
import json
from typing import Dict, Optional
import pynvml  # For NVIDIA GPUs
import psutil  # For general system info

class GPUType:
    NVIDIA = "nvidia"
    AMD = "amd"
    APPLE = "apple"
    UNKNOWN = "unknown"

class GPUMonitor:
    def __init__(self):
        self.gpu_type = self._detect_gpu_type()
        if self.gpu_type == GPUType.NVIDIA:
            try:
                pynvml.nvmlInit()
            except pynvml.NVMLError:
                pass
    
    def _detect_gpu_type(self) -> str:
        """Detect the type of GPU in the system."""
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            # Check for Apple Silicon
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True
                )
                if "Apple" in result.stdout:
                    return GPUType.APPLE
            except:
                pass
        
        # Check for NVIDIA GPU
        try:
            subprocess.run(["nvidia-smi"], capture_output=True)
            return GPUType.NVIDIA
        except:
            pass
        
        # Check for AMD GPU
        try:
            # On Linux, check for AMD GPU
            if system == "linux":
                with open("/proc/cpuinfo", "r") as f:
                    if "AMD" in f.read():
                        return GPUType.AMD
        except:
            pass
        
        return GPUType.UNKNOWN
    
    def get_gpu_info(self) -> Dict:
        """Get information about all available GPUs."""
        if self.gpu_type == GPUType.NVIDIA:
            return self._get_nvidia_gpu_info()
        elif self.gpu_type == GPUType.AMD:
            return self._get_amd_gpu_info()
        elif self.gpu_type == GPUType.APPLE:
            return self._get_apple_gpu_info()
        else:
            return self._get_fallback_gpu_info()
    
    def _get_nvidia_gpu_info(self) -> Dict:
        """Get information about NVIDIA GPUs."""
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            gpu_info = {}
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                gpu_info[i] = {
                    'type': GPUType.NVIDIA,
                    'memory_used': info.used / 1024**3,  # Convert to GB
                    'memory_total': info.total / 1024**3,  # Convert to GB
                    'gpu_utilization': utilization.gpu,
                    'memory_utilization': utilization.memory,
                    'name': pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                }
            
            return gpu_info
        except Exception:
            return self._get_fallback_gpu_info()
    
    def _get_amd_gpu_info(self) -> Dict:
        """Get information about AMD GPUs."""
        try:
            # Try to use rocm-smi if available
            result = subprocess.run(
                ["rocm-smi", "--json"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                gpu_info = {}
                
                for i, gpu in enumerate(data.get('card_list', [])):
                    gpu_info[i] = {
                        'type': GPUType.AMD,
                        'memory_used': float(gpu.get('memory_used', 0)) / 1024,  # Convert to GB
                        'memory_total': float(gpu.get('memory_total', 0)) / 1024,  # Convert to GB
                        'gpu_utilization': float(gpu.get('gpu_utilization', 0)),
                        'memory_utilization': float(gpu.get('memory_utilization', 0)),
                        'name': gpu.get('card_name', 'Unknown AMD GPU')
                    }
                
                return gpu_info
        except:
            pass
        
        return self._get_fallback_gpu_info()
    
    def _get_apple_gpu_info(self) -> Dict:
        """Get information about Apple GPUs."""
        try:
            # Use system_profiler to get GPU info on macOS
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                gpu_info = {}
                
                for i, display in enumerate(data.get('SPDisplaysDataType', [])):
                    if 'Metal: Supported' in str(display):
                        gpu_info[i] = {
                            'type': GPUType.APPLE,
                            'memory_used': 0,  # Apple doesn't provide direct memory info
                            'memory_total': 0,  # Apple doesn't provide direct memory info
                            'gpu_utilization': 0,  # Apple doesn't provide direct utilization info
                            'memory_utilization': 0,  # Apple doesn't provide direct memory utilization info
                            'name': display.get('_name', 'Apple GPU')
                        }
                
                return gpu_info
        except:
            pass
        
        return self._get_fallback_gpu_info()
    
    def _get_fallback_gpu_info(self) -> Dict:
        """Fallback method to get basic GPU information."""
        try:
            # Try to get GPU info from system
            if platform.system().lower() == "linux":
                result = subprocess.run(
                    ["lspci", "-nn"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    gpu_info = {}
                    for i, line in enumerate(result.stdout.split('\n')):
                        if 'VGA' in line or '3D' in line:
                            gpu_info[i] = {
                                'type': GPUType.UNKNOWN,
                                'memory_used': 0,
                                'memory_total': 0,
                                'gpu_utilization': 0,
                                'memory_utilization': 0,
                                'name': line.strip()
                            }
                    return gpu_info
        except:
            pass
        
        # If all else fails, return empty dict
        return {} 