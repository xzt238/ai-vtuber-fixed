"""
自动更新管理器 — GitHub Releases API

功能:
- 检查 GitHub Releases 最新版本
- 比较版本号判断是否需要更新
- 下载更新包（显示进度）
- 支持跳过版本

使用方式:
    manager = UpdateManager("xzt238/ai-vtuber-fixed", current_version="1.9.64")
    manager.check_done.connect(on_check_result)
    manager.download_progress.connect(on_progress)
    manager.download_done.connect(on_download_done)
    manager.check_for_updates()
"""

import os
import json
import tempfile
from PySide6.QtCore import QObject, Signal, QThread


class CheckUpdateWorker(QThread):
    """版本检查线程"""
    check_done = Signal(dict)  # {has_update, latest_version, download_url, release_notes, error}
    error = Signal(str)

    def __init__(self, repo, current_version):
        super().__init__()
        self.repo = repo
        self.current_version = current_version

    def run(self):
        try:
            import urllib.request
            import urllib.error

            url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "GuguGaga-AI-VTuber"})

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            latest = data.get("tag_name", "").lstrip("v")
            html_url = data.get("html_url", "")
            body = data.get("body", "")

            # 查找下载 URL（优先 .zip）
            download_url = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".zip"):
                    download_url = asset.get("browser_download_url", "")
                    break

            has_update = self._compare_versions(latest, self.current_version)

            self.check_done.emit({
                "has_update": has_update,
                "latest_version": latest,
                "current_version": self.current_version,
                "download_url": download_url,
                "release_url": html_url,
                "release_notes": body[:2000] if body else "",
            })
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.check_done.emit({"has_update": False, "error": "暂无发布版本"})
            else:
                self.error.emit(f"检查更新失败: HTTP {e.code}")
        except Exception as e:
            self.error.emit(f"检查更新失败: {e}")

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> bool:
        """比较版本号，v1 > v2 返回 True"""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            # 补齐长度
            while len(parts1) < len(parts2):
                parts1.append(0)
            while len(parts2) < len(parts1):
                parts2.append(0)
            return parts1 > parts2
        except Exception:
            return False


class DownloadWorker(QThread):
    """下载更新包线程"""
    download_progress = Signal(int, int)  # bytes_downloaded, total_bytes
    download_done = Signal(str)  # file_path
    error = Signal(str)

    def __init__(self, url, save_dir=None):
        super().__init__()
        self.url = url
        self.save_dir = save_dir or tempfile.gettempdir()

    def run(self):
        try:
            import urllib.request

            req = urllib.request.Request(self.url, headers={"User-Agent": "GuguGaga-AI-VTuber"})

            with urllib.request.urlopen(req, timeout=60) as response:
                total = int(response.headers.get("Content-Length", 0))
                filename = self.url.split("/")[-1] or "update.zip"
                save_path = os.path.join(self.save_dir, filename)

                downloaded = 0
                chunk_size = 8192

                with open(save_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.download_progress.emit(downloaded, total)

                self.download_done.emit(save_path)
        except Exception as e:
            self.error.emit(f"下载失败: {e}")


class UpdateManager(QObject):
    """
    自动更新管理器

    信号:
        check_done(result): 检查完成
        download_progress(downloaded, total): 下载进度
        download_done(file_path): 下载完成
        error(error_msg): 错误
    """

    check_done = Signal(dict)
    download_progress = Signal(int, int)
    download_done = Signal(str)
    error = Signal(str)

    def __init__(self, repo="xzt238/ai-vtuber-fixed", current_version="1.9.64", parent=None):
        super().__init__(parent)
        self.repo = repo
        self.current_version = current_version
        self._check_worker = None
        self._download_worker = None
        self._skipped_version = None

        # 跳过版本缓存
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._skip_file = os.path.join(project_dir, "app", "cache", "skip_update.json")
        self._load_skip_version()

    def _load_skip_version(self):
        """加载跳过版本"""
        try:
            if os.path.exists(self._skip_file):
                with open(self._skip_file, 'r') as f:
                    data = json.load(f)
                self._skipped_version = data.get("skip_version")
        except Exception:
            pass

    def _save_skip_version(self, version: str):
        """保存跳过版本"""
        self._skipped_version = version
        try:
            os.makedirs(os.path.dirname(self._skip_file), exist_ok=True)
            with open(self._skip_file, 'w') as f:
                json.dump({"skip_version": version}, f)
        except Exception:
            pass

    def check_for_updates(self):
        """检查更新"""
        self._check_worker = CheckUpdateWorker(self.repo, self.current_version)
        self._check_worker.check_done.connect(self._on_check_done)
        self._check_worker.error.connect(self.error.emit)
        self._check_worker.start()

    def _on_check_done(self, result: dict):
        """检查完成回调"""
        # 如果用户跳过了此版本，标记为无更新
        if result.get("has_update") and result.get("latest_version") == self._skipped_version:
            result["has_update"] = False
            result["skipped"] = True
        self.check_done.emit(result)

    def skip_version(self, version: str):
        """跳过指定版本"""
        self._save_skip_version(version)

    def download_update(self, url: str, save_dir: str = None):
        """下载更新包"""
        self._download_worker = DownloadWorker(url, save_dir)
        self._download_worker.download_progress.connect(self.download_progress.emit)
        self._download_worker.download_done.connect(self.download_done.emit)
        self._download_worker.error.connect(self.error.emit)
        self._download_worker.start()

    def open_release_page(self, url: str):
        """打开发布页面"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            self.error.emit(f"无法打开浏览器: {e}")
