from collections import deque
from contextlib import contextmanager
from itertools import tee
import logging
from pathlib import Path
import pickle

LOG_PATH = Path.home() / ".geoecon-logs"


class ProcessLogger:
    def __init__(self, process_name, target_dir=None):
        target_dir = Path(target_dir or LOG_PATH)
        self.log_file = target_dir / f"{process_name}.log"
        self.log_data = target_dir / f"{process_name}.bin"
        self.log_stages = self.load_stages()
        self._open_log_file = None
        
        logging.info("📖- Logging file %s", self.log_file)
        logging.info("💾- Data file %s", self.log_data)

        if not target_dir.exists():
            target_dir.mkdir(parents=True)

    def load_data(self):
        with self.log_data.open("rb") as f:
            return pickle.load(f)

    def save_data(self, data):
        with self.log_data.open("wb+") as f:
            pickle.dump(data, f)

    def load_stages(self):
        log_path = Path(self.log_file)
        if log_path.exists():
            with log_path.open("r") as f:
                return set(l.strip() for l in f.readlines())
        else:
            return set()

    def open(self):
        if self._open_log_file is None:
            self._open_log_file = self.log_file.open("a")
        return self

    def close(self):
        self._open_log_file.close()

    def __enter__(self):
        logging.debug("Starting processor logging")
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.debug("Stopping processor logging")
        self.close()

    def mark_stage(self, stage_name, data=None):
        self._open_log_file.write(f"{stage_name}\n")
        self._open_log_file.flush()
        self.log_stages.add(stage_name)
        if data:
            self.save_data(data)

    def is_stage_complete(self, stage_name):
        return str(stage_name) in self.log_stages

    def stages(self, report, stages, stage_name_function: lambda x: x):
        iter_stages, total_stages = tee(stages) 
        total = 0
        deque((total := total + 1 for _ in total_stages), maxlen=0)
        for i, stage in enumerate(iter_stages):
            stage_name = stage_name_function(*stage) if isinstance(stage, tuple) else stage_name_function(stage)
            if self.is_stage_complete(stage_name):
                logging.info("⏭️-Skipping stage '%s' (%s/%s)", stage_name, i+1, total)
                if report.is_set():
                    logging.info("💾-Loading previous report")
                    report.set_report(self.load_data())
            else:
                logging.info("⚙️-Doing stage '%s' (%s/%s)", stage_name, i+1, total)
                try:
                    yield stage
                except Exception as e:
                    logging.error(f"❌- Error in stage %s (%s/%s): %s", stage_name, i+1, total, e)
                    raise
                else:
                    logging.info("✅-Done stage '%s' (%s/%s)", stage_name, i+1, total)
                    self.mark_stage(stage_name, report.get_report())
