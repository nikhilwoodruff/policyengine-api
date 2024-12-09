from redis import Redis
from rq import Worker

from policyengine_api.utils.worker_logger import WorkerLogger

# Preload libraries
import policyengine_uk
import policyengine_us
import policyengine_canada
import policyengine_ng

# Provide the worker with the list of queues (str) to listen to.
w = Worker(["default"], connection=Redis())
logger = WorkerLogger(id=w.name)
w.work()
