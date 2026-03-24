import time
import threading
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import queue


class ScheduleType(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    INTERVAL = "interval"
    CRON = "cron"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ScheduledTask:
    def __init__(self, task_id: str, name: str, func: Callable, 
                 schedule_type: ScheduleType, schedule_config: Dict[str, Any],
                 enabled: bool = True):
        self.task_id = task_id
        self.name = name
        self.func = func
        self.schedule_type = schedule_type
        self.schedule_config = schedule_config
        self.enabled = enabled
        self.status = TaskStatus.PENDING
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.result: Any = None
        self.thread: Optional[threading.Thread] = None

    def calculate_next_run(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        now = from_time or datetime.now()
        
        if self.schedule_type == ScheduleType.ONCE:
            run_time_str = self.schedule_config.get('time')
            if run_time_str:
                run_time = datetime.strptime(run_time_str, '%Y-%m-%d %H:%M:%S')
                return run_time if run_time > now else None
            return None
        
        elif self.schedule_type == ScheduleType.DAILY:
            time_str = self.schedule_config.get('time', '00:00:00')
            hour, minute, second = map(int, time_str.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        
        elif self.schedule_type == ScheduleType.WEEKLY:
            days = self.schedule_config.get('days', [0])
            time_str = self.schedule_config.get('time', '00:00:00')
            hour, minute, second = map(int, time_str.split(':'))
            
            for i in range(8):
                check_day = (now.weekday() + i) % 7
                if check_day in days:
                    days_ahead = i if i > 0 else 7
                    next_run = now + timedelta(days=days_ahead)
                    next_run = next_run.replace(hour=hour, minute=minute, second=second, microsecond=0)
                    if next_run > now:
                        return next_run
            return None
        
        elif self.schedule_type == ScheduleType.MONTHLY:
            day = self.schedule_config.get('day', 1)
            time_str = self.schedule_config.get('time', '00:00:00')
            hour, minute, second = map(int, time_str.split(':'))
            
            next_run = now.replace(day=day, hour=hour, minute=minute, second=second, microsecond=0)
            if next_run <= now:
                if now.month == 12:
                    next_run = next_run.replace(year=now.year+1, month=1)
                else:
                    next_run = next_run.replace(month=now.month+1)
            return next_run
        
        elif self.schedule_type == ScheduleType.INTERVAL:
            seconds = self.schedule_config.get('seconds', 60)
            if self.last_run:
                return self.last_run + timedelta(seconds=seconds)
            return now + timedelta(seconds=seconds)
        
        return None


class TaskScheduler:
    def __init__(self, max_concurrent: int = 5):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.max_concurrent = max_concurrent
        self.task_queue = queue.Queue()
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.worker_threads: List[threading.Thread] = []
        self.listeners: Dict[str, List[Callable]] = {
            'task_start': [],
            'task_complete': [],
            'task_error': [],
            'task_missed': []
        }

    def add_task(self, task: ScheduledTask):
        self.tasks[task.task_id] = task
        if task.enabled:
            task.next_run = task.calculate_next_run()

    def remove_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.thread and task.thread.is_alive():
                task.status = TaskStatus.CANCELLED
            del self.tasks[task_id]

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[ScheduledTask]:
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[ScheduledTask]:
        return [task for task in self.tasks.values() if task.status == status]

    def enable_task(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.tasks[task_id].next_run = self.tasks[task_id].calculate_next_run()

    def disable_task(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self.tasks[task_id].next_run = None

    def start_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status != TaskStatus.RUNNING:
                task.status = TaskStatus.PENDING
                self.task_queue.put(task)

    def stop_task(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED

    def run_task_now(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            thread = threading.Thread(target=self._execute_task, args=(task,))
            thread.start()

    def start(self):
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            
            for _ in range(self.max_concurrent):
                worker = threading.Thread(target=self._worker_loop)
                worker.daemon = True
                worker.start()
                self.worker_threads.append(worker)

    def stop(self):
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        for worker in self.worker_threads:
            worker.join(timeout=5)

    def _scheduler_loop(self):
        while self.running:
            now = datetime.now()
            
            for task_id, task in self.tasks.items():
                if not task.enabled:
                    continue
                
                if task.status == TaskStatus.RUNNING:
                    continue
                
                if task.next_run and now >= task.next_run:
                    if task.status != TaskStatus.PENDING:
                        task.status = TaskStatus.PENDING
                        self.task_queue.put(task)
            
            time.sleep(1)

    def _worker_loop(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task.status == TaskStatus.PENDING:
                    self._execute_task(task)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")

    def _execute_task(self, task: ScheduledTask):
        task.status = TaskStatus.RUNNING
        self._emit('task_start', task)
        
        try:
            task.result = task.func()
            task.status = TaskStatus.COMPLETED
            task.run_count += 1
            self._emit('task_complete', task, task.result)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_count += 1
            task.last_error = str(e)
            self._emit('task_error', task, e)
        
        task.last_run = datetime.now()
        
        if task.enabled and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.next_run = task.calculate_next_run()

    def add_listener(self, event: str, callback: Callable):
        if event in self.listeners:
            self.listeners[event].append(callback)

    def remove_listener(self, event: str, callback: Callable):
        if event in self.listeners and callback in self.listeners[event]:
            self.listeners[event].remove(callback)

    def _emit(self, event: str, *args, **kwargs):
        if event in self.listeners:
            for callback in self.listeners[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Listener error: {e}")

    def export_tasks(self, file_path: str):
        tasks_data = []
        for task_id, task in self.tasks.items():
            tasks_data.append({
                'task_id': task.task_id,
                'name': task.name,
                'schedule_type': task.schedule_type.value,
                'schedule_config': task.schedule_config,
                'enabled': task.enabled,
                'run_count': task.run_count,
                'error_count': task.error_count,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None
            })
        
        with open(file_path, 'w') as f:
            json.dump(tasks_data, f, indent=2)

    def import_tasks(self, file_path: str):
        with open(file_path, 'r') as f:
            tasks_data = json.load(f)
        
        for task_data in tasks_data:
            task = ScheduledTask(
                task_id=task_data['task_id'],
                name=task_data['name'],
                func=lambda: None,
                schedule_type=ScheduleType(task_data['schedule_type']),
                schedule_config=task_data['schedule_config'],
                enabled=task_data['enabled']
            )
            task.run_count = task_data.get('run_count', 0)
            task.error_count = task_data.get('error_count', 0)
            
            if task_data.get('last_run'):
                task.last_run = datetime.fromisoformat(task_data['last_run'])
            if task_data.get('next_run'):
                task.next_run = datetime.fromisoformat(task_data['next_run'])
            
            self.add_task(task)

    def get_task_history(self, task_id: str, limit: int = 100) -> List[Dict]:
        return []

    def clear_task_history(self, task_id: str):
        pass
