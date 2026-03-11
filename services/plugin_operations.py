"""
Parallel plugin operations manager with cancellation support.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of plugin operations."""
    INSTALL = "install"
    UNINSTALL = "uninstall"
    UPDATE = "update"


class OperationStatus(Enum):
    """Status of plugin operations."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PluginOperation:
    """Represents a single plugin operation."""
    
    def __init__(
        self,
        operation_id: str,
        operation_type: OperationType,
        plugin_name: str,
        data: Dict[str, Any],
        callback: Optional[Callable] = None
    ):
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.plugin_name = plugin_name
        self.data = data
        self.callback = callback
        self.status = OperationStatus.PENDING
        self.result = None
        self.error_message = ""
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "plugin_name": self.plugin_name,
            "status": self.status.value,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class PluginOperationManager(QObject):
    """Manages parallel plugin operations with cancellation support."""
    
    # Signals
    operation_started = pyqtSignal(str)  # operation_id
    operation_completed = pyqtSignal(str, dict)  # operation_id, result
    operation_failed = pyqtSignal(str, str)  # operation_id, error_message
    operation_cancelled = pyqtSignal(str)  # operation_id
    all_operations_completed = pyqtSignal()  # No parameters
    
    def __init__(self, max_workers: int = 3, parent=None):
        super().__init__(parent)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.operations: Dict[str, PluginOperation] = {}
        self.futures: Dict[str, Future] = {}
        self._shutdown = False
        self._lock = threading.Lock()
    
    def submit_operation(
        self,
        operation_type: OperationType,
        plugin_name: str,
        data: Dict[str, Any],
        callback: Optional[Callable] = None
    ) -> str:
        """Submit a plugin operation for execution."""
        import uuid
        
        operation_id = str(uuid.uuid4())
        operation = PluginOperation(operation_id, operation_type, plugin_name, data, callback)
        
        with self._lock:
            self.operations[operation_id] = operation
        
        # Submit to thread pool
        future = self.executor.submit(self._execute_operation, operation)
        
        with self._lock:
            self.futures[operation_id] = future
        
        logger.info("Submitted operation %s: %s %s", operation_id, operation_type.value, plugin_name)
        return operation_id
    
    def _execute_operation(self, operation: PluginOperation) -> Dict[str, Any]:
        """Execute a plugin operation."""
        try:
            # Update status
            with self._lock:
                operation.status = OperationStatus.RUNNING
                operation.started_at = time.time()
            
            self.operation_started.emit(operation.operation_id)
            
            # Execute the actual operation based on type
            if operation.operation_type == OperationType.INSTALL:
                result = self._execute_install(operation)
            elif operation.operation_type == OperationType.UNINSTALL:
                result = self._execute_uninstall(operation)
            elif operation.operation_type == OperationType.UPDATE:
                result = self._execute_update(operation)
            else:
                raise ValueError(f"Unknown operation type: {operation.operation_type}")
            
            # Update status
            with self._lock:
                operation.status = OperationStatus.COMPLETED
                operation.result = result
                operation.completed_at = time.time()
            
            self.operation_completed.emit(operation.operation_id, result)
            return result
            
        except Exception as e:
            # Check if cancelled
            with self._lock:
                if operation.status == OperationStatus.CANCELLED:
                    self.operation_cancelled.emit(operation.operation_id)
                    raise
            
            # Handle failure
            error_msg = str(e)
            with self._lock:
                operation.status = OperationStatus.FAILED
                operation.error_message = error_msg
                operation.completed_at = time.time()
            
            self.operation_failed.emit(operation.operation_id, error_msg)
            raise
    
    def _execute_install(self, operation: PluginOperation) -> Dict[str, Any]:
        """Execute plugin install operation."""
        from services.plugin_installer import PluginInstaller
        
        installer = operation.data["installer"]
        zip_content = operation.data["zip_content"]
        repo_name = operation.data["repo_name"]
        progress_callback = operation.data.get("progress_callback")
        
        result = installer.install_plugin_from_zip(
            zip_content, repo_name, progress_callback, atomic=True
        )
        
        if not result["success"]:
            raise RuntimeError(result["message"])
        
        return result
    
    def _execute_uninstall(self, operation: PluginOperation) -> Dict[str, Any]:
        """Execute plugin uninstall operation."""
        from services.plugin_installer import PluginInstaller
        
        installer = operation.data["installer"]
        plugin_name = operation.data["plugin_name"]
        
        result = installer.uninstall_plugin(plugin_name)
        
        if not result["success"]:
            raise RuntimeError(result["message"])
        
        return result
    
    def _execute_update(self, operation: PluginOperation) -> Dict[str, Any]:
        """Execute plugin update operation (uninstall + install)."""
        # First uninstall
        uninstall_data = {
            "installer": operation.data["installer"],
            "plugin_name": operation.data["plugin_name"]
        }
        uninstall_op = PluginOperation(
            f"{operation.operation_id}_uninstall",
            OperationType.UNINSTALL,
            operation.plugin_name,
            uninstall_data
        )
        self._execute_uninstall(uninstall_op)
        
        # Then install
        install_data = {
            "installer": operation.data["installer"],
            "zip_content": operation.data["zip_content"],
            "repo_name": operation.data["repo_name"],
            "progress_callback": operation.data.get("progress_callback")
        }
        install_op = PluginOperation(
            f"{operation.operation_id}_install",
            OperationType.INSTALL,
            operation.plugin_name,
            install_data
        )
        return self._execute_install(install_op)
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a pending or running operation."""
        with self._lock:
            if operation_id not in self.operations:
                return False
            
            operation = self.operations[operation_id]
            
            # Can only cancel if not completed
            if operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED]:
                return False
            
            # Mark as cancelled
            operation.status = OperationStatus.CANCELLED
            operation.completed_at = time.time()
            
            # Cancel the future if it's still pending
            if operation_id in self.futures:
                future = self.futures[operation_id]
                if future.cancel():
                    logger.info("Cancelled pending operation %s", operation_id)
                    self.operation_cancelled.emit(operation_id)
                    return True
        
        logger.info("Marked operation %s for cancellation", operation_id)
        return True
    
    def cancel_all_operations(self) -> int:
        """Cancel all pending operations."""
        cancelled_count = 0
        
        with self._lock:
            operation_ids = list(self.operations.keys())
        
        for operation_id in operation_ids:
            if self.cancel_operation(operation_id):
                cancelled_count += 1
        
        logger.info("Cancelled %d operations", cancelled_count)
        return cancelled_count
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an operation."""
        with self._lock:
            if operation_id not in self.operations:
                return None
            return self.operations[operation_id].to_dict()
    
    def get_all_operations(self) -> List[Dict[str, Any]]:
        """Get all operations."""
        with self._lock:
            return [op.to_dict() for op in self.operations.values()]
    
    def get_pending_operations(self) -> List[Dict[str, Any]]:
        """Get pending operations."""
        with self._lock:
            return [
                op.to_dict() for op in self.operations.values()
                if op.status == OperationStatus.PENDING
            ]
    
    def get_running_operations(self) -> List[Dict[str, Any]]:
        """Get running operations."""
        with self._lock:
            return [
                op.to_dict() for op in self.operations.values()
                if op.status == OperationStatus.RUNNING
            ]
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all operations to complete."""
        start_time = time.time()
        
        while True:
            with self._lock:
                running = [
                    op for op in self.operations.values()
                    if op.status in [OperationStatus.PENDING, OperationStatus.RUNNING]
                ]
            
            if not running:
                self.all_operations_completed.emit()
                return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            time.sleep(0.1)
    
    def shutdown(self, wait: bool = True):
        """Shutdown the operation manager."""
        self._shutdown = True
        self.cancel_all_operations()
        
        if wait:
            self.executor.shutdown(wait=True)
        else:
            self.executor.shutdown(wait=False)
        
        logger.info("Plugin operation manager shutdown")
