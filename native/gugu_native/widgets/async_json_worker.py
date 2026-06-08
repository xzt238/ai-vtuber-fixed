"""异步 JSON 读取 Worker

在后台线程中读取多个 JSON 文件，通过信号回传结果到主线程。
"""
from PySide6.QtCore import QThread, Signal
import json


class AsyncJsonWorker(QThread):
    """异步 JSON 读取工作线程"""

    json_loaded = Signal(dict)   # {file_path: data_dict}
    json_failed = Signal(str)    # error message

    def __init__(self, file_paths: list[str], parent=None) -> None:
        super().__init__(parent)
        self._file_paths = file_paths

    def run(self) -> None:
        results = {}
        try:
            for fp in self._file_paths:
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        results[fp] = json.load(f)
                except Exception as e:
                    results[fp] = None  # 或记录错误
            self.json_loaded.emit(results)
        except Exception as e:
            self.json_failed.emit(str(e))
