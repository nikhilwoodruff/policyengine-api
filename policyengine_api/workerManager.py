import google.cloud.logging as cloud_logging
import multiprocessing
import os
from redis import Redis
from rq import Queue, Worker, cancel_job
from rq.job import Job

# from rq.worker import WorkerStatus
from typing import List, Optional
from datetime import datetime


class WorkerManager:
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 5000,
        queue_name: str = "default",
        project_id: str = None,
    ):
        """
        Initialize Redis Queue Manager

        Args:
            redis_host (str): Redis server host
            redis_port (int): Redis server port
            queue_name (str): Name of the queue
            project_id (str): Google Cloud project ID
        """
        # Redis configuration
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.queue_name = queue_name

        # Initialize Redis connection
        try:
            self.redis_conn = Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
            )
            self.queue = Queue(queue_name, connection=self.redis_conn)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

        # Google Cloud Logging client
        self.logging_client = cloud_logging.Client(project=project_id)
        self.logger = self.logging_client.logger("worker_manager")

        # Worker tracking
        self.workers = []

    def log_event(self, message: str, severity: str = "INFO", **kwargs):
        """
        Log an event to Google Cloud Logging

        Args:
            message (str): Log message
            severity (str): Log severity level
            **kwargs: Additional log data
        """

        log_data = {
            "timestamp": datetime.isoformat(),
            "message": message,
            **kwargs,
        }

        self.logger.log_struct(log_data, severity=severity)

    def start_workers(self, num_workers: Optional[int] = None):
        """Start worker processes for the queue
        Args:
            num_workers (int, optional): Number of workers to start.
                                       Defaults to CPU count - 1
        """
        if num_workers is None:
            num_workers = max(1, multiprocessing.cpu_count() - 1)

        def worker_process():
            worker = Worker(
                [self.queue],
                connection=self.redis_conn,
                name=f"microsim-worker-{os.getpid()}",
            )

            def log_job_status(job, status):
                self.log_event(
                    f"Microsimulation {status}",
                    job_id=job.id,
                    worker_pid=os.getpid(),
                    status=status,
                )

            # Register status handlers
            worker.push_job_success = lambda job: log_job_status(
                job, "completed"
            )
            worker.push_job_failure = lambda job: log_job_status(job, "failed")

            worker.work()

        for _ in range(num_workers):
            worker = multiprocessing.Process(target=worker_process)
            worker.start()
            self.workers.append(worker)

            self.log_event("Worker started", worker_pid=worker.pid)

    def enqueue_micosim(self, microsim_func, *args, **kwargs) -> str:
        """
        Enqueue a microsimulation job

        Args:
            microsim_func: The microsimulation function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            str: Job ID for the microsimulation run
        """
        try:
            job = self.queue.enqueue(
                microsim_func,
                args=args,
                kwargs=kwargs,
                job_timeout="1h",  # Adjustable timeout
            )

            self.log_event(
                "Microsimulation enqueued",
                job_id=job.id,
                args=str(args),
                kwargs=str(kwargs),
            )

            return job.id
        except Exception as e:
            self.log_event(
                f"Failed to enqueue microsimulation: {str(e)}",
                severity="Error",
                error=str(e),
            )
            raise

    def cancel_run(self, run_id: str) -> bool:
        """
        Cancel a running microsimulation

        Args:
            run_id (str): The job ID to cancel

        Returns:
            bool: True if cancelled successfully, False otherwise
        """
        try:
            # Get job instance
            job = Job.fetch(run_id, connection=self.redis_conn)

            # Check if job exists and is cancellable
            if job is None:
                self.log_event(
                    "Job not found", severity="WARNING", job_id=run_id
                )
                return False

            # Cancel the job
            cancel_job(run_id, connection=self.redis_conn)

            self.log_event("Microsimulation cancelled", job_id=run_id)

            return True

        except Exception as e:
            self.log_event(
                f"Failed to cancel microsimulation: {str(e)}",
                severity="ERROR",
                job_id=run_id,
                error=str(e),
            )
            return False

    def get_run_status(self, run_id: str) -> dict:
        """
        Get the status of a microsimulation run

        Args:
            run_id (str): The job ID to check

        Returns:
            dict: Status information for the run
        """
        try:
            job = Job.fetch(run_id, connection=self.redis_conn)

            if job is None:
                return {"status": "not found"}

            return {
                "id": run_id,
                "status": job.get_status(),
                "created_at": (
                    job.created_at.isoformat() if job.created_at else None
                ),
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "exc_info": job.exc_info if job.is_failed else None,
            }

        except Exception as e:
            self.log_event(
                f"Failed to get run status: {str(e)}",
                severity="ERROR",
                job_id=run_id,
                error=str(e),
            )
            return {"status": "error", "message": str(e)}

    def cleanup(self):
        """Stop all workers and cleanup resources"""
        for worker in self.workers:
            if worker.is_alive():
                worker.terminate()
                worker.join()

        self.log_event("Workers stopped")
