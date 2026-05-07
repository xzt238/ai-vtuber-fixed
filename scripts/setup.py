#!/usr/bin/env python3
"""
GuguGaga AI-VTuber - One-Click Setup Script

All-in-one: embedded Python, dependencies, models, verification.
No more cmd.exe parsing nightmares - everything runs in Python!

Usage:
  python setup.py              Full setup (recommended)
  python setup.py --deps       Install/reinstall dependencies only
  python setup.py --models     Download models only
  python setup.py --verify     Run verification check only
"""

import sys
import os
import subprocess
import urllib.request
import time
import shutil
import zipfile
import tempfile

# ================================================================
#  Configuration
# ================================================================

PIP_MIRROR_URL = 'https://pypi.tuna.tsinghua.edu.cn/simple'
PIP_TRUSTED = 'pypi.tuna.tsinghua.edu.cn'
TORCH_MIRROR = 'https://mirrors.aliyun.com/pytorch-wheels/cu124'
HF_MIRROR = 'https://hf-mirror.com'

# (import_name, pip_spec, level)
PACKAGES = [
    # Core
    ('yaml', 'pyyaml>=6.0', 'required'),
    ('requests', 'requests>=2.28.0', 'required'),
    ('edge_tts', 'edge-tts>=7.0', 'required'),
    ('websocket_server', 'websocket-server>=0.6', 'required'),
    ('websockets', 'websockets>=10.0', 'required'),
    ('numpy', 'numpy>=1.24.0,<2.0.0', 'required'),
    ('PIL', 'pillow>=10.0', 'required'),
    ('soundfile', 'soundfile', 'required'),
    ('jieba', 'jieba>=0.42', 'required'),
    ('transformers', 'transformers>=4.44.0,<4.45.0', 'required'),
    ('peft', 'peft>=0.10.0', 'required'),
    ('accelerate', 'accelerate>=0.20.0', 'required'),
    ('pytorch_lightning', 'pytorch-lightning>=2.4', 'required'),
    ('matplotlib', 'matplotlib', 'required'),
    # ASR
    ('faster_whisper', 'faster-whisper>=1.0', 'recommended'),
    ('funasr', 'funasr>=1.0', 'recommended'),
    ('sounddevice', 'sounddevice>=0.4', 'recommended'),
    # Vision/OCR
    ('cv2', 'opencv-python>=4.8', 'optional'),
    ('rapidocr_onnxruntime', 'rapidocr-onnxruntime>=1.3.0', 'optional'),
    ('modelscope', 'modelscope>=1.9.0', 'optional'),
    # Memory
    ('sentence_transformers', 'sentence-transformers>=2.0', 'optional'),
    ('chromadb', 'chromadb', 'optional'),
    # GPT-SoVITS
    ('bitsandbytes', 'bitsandbytes', 'optional'),
    ('gradio', 'gradio>=4.0,<5', 'optional'),
    ('scipy', 'scipy', 'optional'),
    ('librosa', 'librosa==0.10.2', 'optional'),
    ('numba', 'numba', 'optional'),
    ('cn2an', 'cn2an', 'optional'),
    ('pypinyin', 'pypinyin', 'optional'),
    ('sentencepiece', 'sentencepiece', 'optional'),
    ('chardet', 'chardet', 'optional'),
    ('psutil', 'psutil', 'optional'),
    ('split_lang', 'split-lang', 'optional'),
    ('fast_langdetect', 'fast-langdetect>=0.3.1', 'optional'),
    ('wordsegment', 'wordsegment', 'optional'),
    ('rotary_embedding_torch', 'rotary-embedding-torch', 'optional'),
    ('opencc', 'OpenCC-python-reimplemented', 'optional'),
    ('x_transformers', 'x_transformers', 'optional'),
    ('torchmetrics', 'torchmetrics<=1.5', 'optional'),
    ('ctranslate2', 'ctranslate2>=4.0,<5', 'optional'),
    ('av', 'av>=11', 'optional'),
    ('ffmpeg', 'ffmpeg-python', 'optional'),
    ('tiktoken', 'tiktoken', 'optional'),
    ('mss', 'mss>=10.0', 'optional'),
    # Windows
    ('win32api', 'pywin32>=306', 'optional'),
    # Native Desktop (PySide6)
    ('PySide6', 'PySide6>=6.6', 'recommended'),
    ('qfluentwidgets', 'PySide6-Fluent-Widgets>=1.7', 'recommended'),
    # Live2D (optional — requires live2d-py, may need manual install)
    ('live2d', 'live2d-py', 'optional'),
    # ChatTTS (optional — 对话场景 TTS, CC BY-NC 4.0)
    ('ChatTTS', 'ChatTTS', 'optional'),
]

# ================================================================
#  Formatting Helpers
# ================================================================

def format_size(n):
    if n < 1024: return f"{n} B"
    if n < 1024*1024: return f"{n/1024:.1f} KB"
    if n < 1024*1024*1024: return f"{n/1024/1024:.1f} MB"
    return f"{n/1024/1024/1024:.2f} GB"

def format_speed(bps):
    if bps < 1024: return f"{bps:.0f} B/s"
    if bps < 1024*1024: return f"{bps/1024:.1f} KB/s"
    return f"{bps/1024/1024:.1f} MB/s"

def format_time(secs):
    if secs < 0 or secs > 99999: return "--:--"
    if secs < 60: return f"{int(secs)}s"
    if secs < 3600:
        m, s = divmod(int(secs), 60)
        return f"{m}m{s:02d}s"
    h, r = divmod(int(secs), 3600)
    m, s = divmod(r, 60)
    return f"{h}h{m:02d}m"

def print_header(step, total, title):
    print()
    print(f"  [{step}/{total}] {title}")
    print(f"  {'-'*50}")
    print()

# ================================================================
#  Download with Progress
# ================================================================

def download_file(url, dest, desc=None):
    """Download a file with progress bar. Returns True on success."""
    if desc is None:
        desc = os.path.basename(dest)

    print(f"  Downloading: {desc}")
    print(f"  URL: {url}")

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            done = 0
            start = time.time()

            dest_dir = os.path.dirname(os.path.abspath(dest))
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)

            with open(dest, 'wb') as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    done += len(chunk)
                    f.write(chunk)

                    if total > 0:
                        pct = done / total
                        bw = 30
                        filled = int(bw * pct)
                        bar = '=' * filled + '>' + ' ' * (bw - filled - 1)
                        elapsed = time.time() - start
                        speed = done / elapsed if elapsed > 0 else 0
                        eta = (total - done) / speed if speed > 0 else 0
                        sys.stdout.write(
                            f"\r  [{bar}] {pct*100:5.1f}%  "
                            f"{format_size(done)}/{format_size(total)}  "
                            f"{format_speed(speed)}  ETA {format_time(eta)}   "
                        )
                    else:
                        elapsed = time.time() - start
                        speed = done / elapsed if elapsed > 0 else 0
                        sys.stdout.write(f"\r  {format_size(done)}  {format_speed(speed)}   ")
                    sys.stdout.flush()

        elapsed = time.time() - start
        avg = done / elapsed if elapsed > 0 else 0
        print()
        print(f"  [OK] {desc} - {format_size(done)} in {format_time(elapsed)} (avg {format_speed(avg)})")
        return True
    except Exception as e:
        print(f"\n  [XX] Download failed: {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False


def download_and_extract_zip(url, extract_to, rename_from=None, rename_to=None, desc=None):
    """Download zip, extract, optionally rename dir inside. Returns True on success."""
    if desc is None:
        desc = os.path.basename(extract_to)

    zip_path = os.path.join(tempfile.gettempdir(), '_gugugaga_dl.zip')
    if not download_file(url, zip_path, desc):
        return False

    try:
        parent = os.path.dirname(os.path.abspath(extract_to))
        os.makedirs(parent, exist_ok=True)

        print("  Extracting...", end='', flush=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(parent)

        if rename_from and rename_to:
            src = os.path.join(parent, rename_from)
            dst = os.path.join(parent, rename_to)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            os.rename(src, dst)

        os.remove(zip_path)
        print(" Done!")
        print(f"  [OK] {desc} extracted")
        return True
    except Exception as e:
        print(f"\n  [XX] Extract failed: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return False

# ================================================================
#  Python Detection
# ================================================================

def find_python(project_root):
    """Find a working Python. Returns list for subprocess.run, e.g. ['python\\python.exe'] or ['py', '-3.11']."""
    # 1. Embedded Python (preferred)
    embedded = os.path.join(project_root, 'python', 'python.exe')
    if os.path.exists(embedded):
        return [embedded]

    # 2. py launcher -3.11
    try:
        r = subprocess.run(['py', '-3.11', '--version'], capture_output=True, timeout=5)
        if r.returncode == 0:
            return ['py', '-3.11']
    except Exception:
        pass

    # 3. Generic python
    try:
        r = subprocess.run(['python', '--version'], capture_output=True, timeout=5)
        if r.returncode == 0:
            return ['python']
    except Exception:
        pass

    return None

# ================================================================
#  Embedded Python Setup
# ================================================================

def setup_embedded_python(project_root):
    """Download and set up embedded Python 3.11. Returns path to python.exe or None."""
    python_dir = os.path.join(project_root, 'python')
    python_exe = os.path.join(python_dir, 'python.exe')

    if os.path.exists(python_exe):
        print("  [OK] Embedded Python already exists")
        return python_exe

    print("  Embedded Python not found, downloading...")
    os.makedirs(python_dir, exist_ok=True)

    # Download
    zip_url = 'https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip'
    zip_path = os.path.join(python_dir, 'python-3.11.9-embed-amd64.zip')
    if not download_file(zip_url, zip_path, "Python 3.11.9 embedded (~10MB)"):
        return None

    # Extract
    print("  Extracting...", end='', flush=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(python_dir)
    os.remove(zip_path)
    print(" Done!")

    # Configure _pth
    print("  Configuring paths...", end='', flush=True)
    pth_path = os.path.join(python_dir, 'python311._pth')
    with open(pth_path, 'w') as f:
        f.write('python311.zip\nLib\nLib\\site-packages\n..\nimport site\n')
    print(" Done!")

    # Install pip
    print("  Installing pip...", end='', flush=True)
    get_pip_path = os.path.join(python_dir, 'get-pip.py')
    try:
        urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', get_pip_path)
        subprocess.run(
            [python_exe, get_pip_path,
             '-i', PIP_MIRROR_URL, '--trusted-host', PIP_TRUSTED],
            capture_output=True, timeout=120
        )
    except Exception as e:
        print(f" pip install warning: {e}")
    if os.path.exists(get_pip_path):
        os.remove(get_pip_path)
    print(" Done!")

    print("  [OK] Embedded Python installed!")
    return python_exe

# ================================================================
#  Package Installation
# ================================================================

def pip_install(python, args, timeout=600):
    """Run pip install with given args. Returns returncode."""
    cmd = python + ['-m', 'pip', 'install'] + args
    try:
        return subprocess.run(cmd, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return -1

def check_import(python, module_name):
    """Check if a Python module can be imported."""
    try:
        r = subprocess.run(
            python + ['-c', f'import {module_name}'],
            capture_output=True, timeout=10
        )
        return r.returncode == 0
    except Exception:
        return False

def install_package(python, import_name, pip_spec, level):
    """Install a single pip package. Returns 'ok', 'skip', or 'fail'."""
    if check_import(python, import_name):
        print(f"    [OK] {import_name} - already installed")
        return 'skip'

    print(f"    Installing {import_name} ({pip_spec})...")

    mirror_args = ['-i', PIP_MIRROR_URL, '--trusted-host', PIP_TRUSTED]

    # First try: with mirror
    rc = pip_install(python, [pip_spec] + mirror_args)
    if rc == 0:
        print(f"    [OK] {import_name}")
        return 'ok'

    # Second try: default PyPI
    print(f"    Retry {import_name} with default PyPI...")
    rc = pip_install(python, [pip_spec])
    if rc == 0:
        print(f"    [OK] {import_name}")
        return 'ok'

    # Failed
    if level == 'required':
        print(f"    [XX] {import_name} FAILED (required!)")
    else:
        print(f"    [--] {import_name} failed ({level}, core still works)")
    return 'fail'

def install_pytorch_cuda(python):
    """Install PyTorch CUDA cu124. Returns True on success."""
    try:
        r = subprocess.run(
            python + ['-c', 'import torch; assert torch.cuda.is_available()'],
            capture_output=True, timeout=10
        )
        if r.returncode == 0:
            v = subprocess.run(
                python + ['-c', 'import torch; print(torch.__version__)'],
                capture_output=True, text=True, timeout=10
            )
            print(f"    [OK] PyTorch CUDA {v.stdout.strip()} already available")
            return True
    except Exception:
        pass

    print("    PyTorch CUDA not available, installing...")
    print("    (This may take 5-15 minutes, ~2GB download)")

    # Install new version first - pip handles upgrade automatically
    # NEVER uninstall before install - if install fails, we lose the old version too
    #
    # CRITICAL: Must use --find-links (not --index-url) with Aliyun mirror.
    # Aliyun's directory is NOT a PEP 503 compliant index, so --index-url fails.
    # Also MUST pin version with +cu124 suffix (e.g. torch==2.6.0+cu124),
    # otherwise pip picks the latest CPU-only version from PyPI.
    TORCH_CUDA_VERSION = '2.6.0+cu124'
    TORCHAUDIO_CUDA_VERSION = '2.6.0+cu124'
    TORCHVISION_CUDA_VERSION = '0.21.0+cu124'
    rc = pip_install(
        python,
        [f'torch=={TORCH_CUDA_VERSION}',
         f'torchaudio=={TORCHAUDIO_CUDA_VERSION}',
         f'torchvision=={TORCHVISION_CUDA_VERSION}',
         '--find-links', TORCH_MIRROR],
        timeout=1800
    )
    if rc == 0:
        # Verify CUDA actually works
        try:
            v = subprocess.run(
                python + ['-c', 'import torch; assert torch.cuda.is_available()'],
                capture_output=True, timeout=30
            )
            if v.returncode == 0:
                print("    [OK] PyTorch CUDA installed")
                return True
            else:
                print("    [XX] PyTorch installed but CUDA not available (GPU driver issue?)")
                return False
        except Exception:
            print("    [XX] PyTorch installed but CUDA check failed")
            return False

    # Fallback: try with --extra-index-url (keeps PyPI as secondary source)
    print("    Retrying with --extra-index-url...")
    rc = pip_install(
        python,
        [f'torch=={TORCH_CUDA_VERSION}',
         f'torchaudio=={TORCHAUDIO_CUDA_VERSION}',
         f'torchvision=={TORCHVISION_CUDA_VERSION}',
         '--extra-index-url', TORCH_MIRROR],
        timeout=1800
    )
    if rc == 0:
        try:
            v = subprocess.run(
                python + ['-c', 'import torch; assert torch.cuda.is_available()'],
                capture_output=True, timeout=30
            )
            if v.returncode == 0:
                print("    [OK] PyTorch CUDA installed (fallback)")
                return True
        except Exception:
            pass

    print("    [XX] PyTorch CUDA install failed (GPU inference unavailable)")
    return False

def unlock_dlls(project_root):
    """Unlock DLL security marks on pip-downloaded binaries."""
    print("    Unlocking DLL security marks...")
    pkg_dirs = [
        os.path.join(project_root, 'python', 'Lib', 'site-packages', d)
        for d in ('torch', 'funasr', 'rapidocr_onnxruntime')
    ]
    for d in pkg_dirs:
        if os.path.exists(d):
            try:
                subprocess.run(
                    ['powershell', '-Command',
                     f"Get-ChildItem '{d}' -Recurse -Include *.dll,*.pyd "
                     f"-ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"],
                    capture_output=True, timeout=30
                )
            except Exception:
                pass
    print("    [OK] DLLs unlocked")

# ================================================================
#  Model Download
# ================================================================

def check_model_file(path, min_size):
    """Check if a model file exists and is larger than min_size bytes."""
    if not os.path.exists(path):
        return False
    try:
        return os.path.getsize(path) > min_size
    except Exception:
        return False

def download_models(project_root):
    """Download all required model files. Returns dict with stats."""
    pretrained_dir = os.path.join(project_root, 'GPT-SoVITS', 'GPT_SoVITS', 'pretrained_models')
    os.makedirs(pretrained_dir, exist_ok=True)

    stats = {'ok': 0, 'skip': 0, 'fail': 0}

    # --- s2Gv3.pth ---
    s2g = os.path.join(pretrained_dir, 's2Gv3.pth')
    if check_model_file(s2g, 100_000_000):
        print(f"    [OK] s2Gv3.pth already exists ({format_size(os.path.getsize(s2g))})")
        stats['skip'] += 1
    else:
        if os.path.exists(s2g):
            print("    [--] s2Gv3.pth corrupted (too small), re-downloading...")
            os.remove(s2g)
        if download_file(
            f"{HF_MIRROR}/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s2Gv3.pth",
            s2g, "s2Gv3.pth (~733MB)"
        ):
            stats['ok'] += 1
        else:
            print("    Manual: https://hf-mirror.com/jackal119/GPT-SoVITS-v3")
            stats['fail'] += 1

    # --- s1v3.ckpt (GPT v3/v4 pretrained model) ---
    s1v = os.path.join(pretrained_dir, 's1v3.ckpt')
    if check_model_file(s1v, 100_000_000):
        print(f"    [OK] s1v3.ckpt already exists ({format_size(os.path.getsize(s1v))})")
        stats['skip'] += 1
    else:
        if os.path.exists(s1v):
            print("    [--] s1v3.ckpt corrupted (too small), re-downloading...")
            os.remove(s1v)
        if download_file(
            f"{HF_MIRROR}/kevinwang676/GPT-SoVITS-v3/resolve/main/GPT_SoVITS/pretrained_models/s1v3.ckpt",
            s1v, "s1v3.ckpt (~621MB)"
        ):
            stats['ok'] += 1
        else:
            print("    Manual: https://hf-mirror.com/kevinwang676/GPT-SoVITS-v3")
            stats['fail'] += 1

    # --- chinese-hubert-base ---
    hubert_dir = os.path.join(pretrained_dir, 'chinese-hubert-base')
    hubert = os.path.join(hubert_dir, 'pytorch_model.bin')
    if check_model_file(hubert, 100_000_000):
        print(f"    [OK] chinese-hubert-base already exists ({format_size(os.path.getsize(hubert))})")
        stats['skip'] += 1
    else:
        os.makedirs(hubert_dir, exist_ok=True)
        if download_file(
            f"{HF_MIRROR}/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin",
            hubert, "chinese-hubert-base (~1.2GB)"
        ):
            stats['ok'] += 1
        else:
            stats['fail'] += 1

    # --- G2PW ---
    g2pw_dir = os.path.join(project_root, 'GPT-SoVITS', 'GPT_SoVITS', 'text', 'G2PWModel')
    g2pw = os.path.join(g2pw_dir, 'g2pW.onnx')
    if check_model_file(g2pw, 1_000_000):
        print(f"    [OK] G2PW model already exists ({format_size(os.path.getsize(g2pw))})")
        stats['skip'] += 1
    else:
        if os.path.exists(g2pw_dir):
            shutil.rmtree(g2pw_dir)
        if download_and_extract_zip(
            'https://www.modelscope.cn/models/kamiorinn/g2pw/resolve/master/G2PWModel_1.1.zip',
            g2pw_dir, 'G2PWModel_1.1', 'G2PWModel', 'G2PW model'
        ):
            stats['ok'] += 1
        else:
            stats['fail'] += 1

    # --- BigVGAN v2 (v3 声码器) ---
    bigvgan_dir = os.path.join(pretrained_dir, 'models--nvidia--bigvgan_v2_24khz_100band_256x')
    bigvgan_generator = os.path.join(bigvgan_dir, 'bigvgan_generator.pt')
    bigvgan_config = os.path.join(bigvgan_dir, 'config.json')
    if check_model_file(bigvgan_generator, 100_000_000) and check_model_file(bigvgan_config, 100):
        print(f"    [OK] BigVGAN v2 already exists ({format_size(os.path.getsize(bigvgan_generator))})")
        stats['skip'] += 1
    else:
        os.makedirs(bigvgan_dir, exist_ok=True)
        dl_ok = True
        if not check_model_file(bigvgan_config, 100):
            if not download_file(
                f"{HF_MIRROR}/nvidia/bigvgan_v2_24khz_100band_256x/resolve/main/config.json",
                bigvgan_config, "BigVGAN v2 config.json"
            ):
                dl_ok = False
        if dl_ok and not check_model_file(bigvgan_generator, 100_000_000):
            if not download_file(
                f"{HF_MIRROR}/nvidia/bigvgan_v2_24khz_100band_256x/resolve/main/bigvgan_generator.pt",
                bigvgan_generator, "BigVGAN v2 generator (~450MB)"
            ):
                dl_ok = False
        if dl_ok:
            stats['ok'] += 1
        else:
            print("    Manual: https://hf-mirror.com/nvidia/bigvgan_v2_24khz_100band_256x")
            stats['fail'] += 1

    # --- SV 说话人验证 (ERes2NetV2) ---
    sv_dir = os.path.join(pretrained_dir, 'sv')
    sv_file = os.path.join(sv_dir, 'pretrained_eres2netv2w24s4ep4.ckpt')
    if check_model_file(sv_file, 100_000_000):
        print(f"    [OK] SV model (ERes2NetV2) already exists ({format_size(os.path.getsize(sv_file))})")
        stats['skip'] += 1
    else:
        os.makedirs(sv_dir, exist_ok=True)
        if download_file(
            f"{HF_MIRROR}/lj1995/GPT-SoVITS/resolve/main/sv/pretrained_eres2netv2w24s4ep4.ckpt",
            sv_file, "SV model ERes2NetV2 (~103MB)"
        ):
            stats['ok'] += 1
        else:
            print("    Manual: https://hf-mirror.com/lj1995/GPT-SoVITS")
            stats['fail'] += 1

    return stats


def download_chattts_models(project_root):
    """下载 ChatTTS 模型文件（通过 HuggingFace mirror）。

    ChatTTS 首次 load() 时会自动下载模型，但国内直连 HuggingFace 很慢。
    这里预先通过 hf-mirror 下载到 HF_HOME 缓存目录，避免首次使用时等待。

    模型约 1.5GB，包含:
    - ChatTTS_u7n.ckpt (decoder)
    - ChatTTS_dvnn.ckpt (VQ decoder)
    等
    """
    stats = {'ok': 0, 'skip': 0, 'fail': 0}

    # ChatTTS 模型缓存目录
    hf_home = os.path.join(project_root, '.cache', 'huggingface')
    chattts_dir = os.path.join(hf_home, 'hub', 'models--2Noise--ChatTTS')
    snapshots_dir = os.path.join(chattts_dir, 'snapshots')

    # 检查是否已经下载过（snapshots 目录存在且非空）
    if os.path.isdir(snapshots_dir) and os.listdir(snapshots_dir):
        print(f"    [OK] ChatTTS 模型已缓存")
        stats['skip'] += 1
        return stats

    # 检查 ChatTTS 是否已安装
    python = find_python(project_root)
    if not python:
        print("    [--] ChatTTS 跳过（未找到 Python）")
        stats['fail'] += 1
        return stats

    try:
        r = subprocess.run(
            python + ['-c', 'import ChatTTS'],
            capture_output=True, timeout=10
        )
        if r.returncode != 0:
            print("    [--] ChatTTS 跳过（ChatTTS 包未安装，请先 pip install ChatTTS）")
            stats['skip'] += 1
            return stats
    except Exception:
        stats['skip'] += 1
        return stats

    # 通过 ChatTTS 自带下载器 + HF mirror 预下载模型
    print("    正在预下载 ChatTTS 模型（~1.5GB，使用 hf-mirror.com 镜像）...")
    print("    这可能需要 5-15 分钟，取决于网络速度")

    try:
        # 设置环境变量使用国内镜像
        env = os.environ.copy()
        env['HF_HOME'] = hf_home
        env['HF_ENDPOINT'] = HF_MIRROR

        r = subprocess.run(
            python + ['-c',
                      'import os; os.environ["HF_ENDPOINT"]="' + HF_MIRROR + '"; '
                      'import ChatTTS; chat=ChatTTS.Chat(); chat.load(compile=False)'],
            env=env,
            timeout=1800  # 30 分钟超时
        )

        if r.returncode == 0:
            print("    [OK] ChatTTS 模型下载完成")
            stats['ok'] += 1
        else:
            print("    [XX] ChatTTS 模型下载失败")
            stats['fail'] += 1
    except subprocess.TimeoutExpired:
        print("    [XX] ChatTTS 模型下载超时（30分钟）")
        stats['fail'] += 1
    except Exception as e:
        print(f"    [XX] ChatTTS 模型下载异常: {e}")
        stats['fail'] += 1

    return stats

# ================================================================
#  Verification
# ================================================================

def run_verification(python, project_root):
    """Run verification checks. Returns dict with counts."""
    results = {'ok': 0, 'fail': 0, 'warn': 0}

    # Embedded Python
    if os.path.exists(os.path.join(project_root, 'python', 'python.exe')):
        print("    [OK] Embedded Python")
        results['ok'] += 1
    else:
        print("    [XX] Embedded Python - MISSING")
        results['fail'] += 1

    # pip
    try:
        r = subprocess.run(python + ['-m', 'pip', '--version'], capture_output=True, timeout=10)
        if r.returncode == 0:
            print("    [OK] pip")
            results['ok'] += 1
        else:
            print("    [XX] pip - MISSING")
            results['fail'] += 1
    except Exception:
        print("    [XX] pip - MISSING")
        results['fail'] += 1

    # PyTorch CUDA
    try:
        r = subprocess.run(
            python + ['-c', 'import torch; assert torch.cuda.is_available()'],
            capture_output=True, timeout=10
        )
        if r.returncode == 0:
            v = subprocess.run(
                python + ['-c', 'import torch; print(torch.__version__)'],
                capture_output=True, text=True, timeout=10
            )
            print(f"    [OK] PyTorch CUDA {v.stdout.strip()}")
            results['ok'] += 1
        else:
            print("    [--] PyTorch CUDA - NOT AVAILABLE (CPU mode)")
            results['warn'] += 1
    except Exception:
        print("    [--] PyTorch CUDA - NOT AVAILABLE (CPU mode)")
        results['warn'] += 1

    # Core packages
    for imp_name, _, level in PACKAGES:
        if level == 'required':
            if check_import(python, imp_name):
                print(f"    [OK] {imp_name}")
                results['ok'] += 1
            else:
                print(f"    [XX] {imp_name} - MISSING")
                results['fail'] += 1

    # Model files
    pretrained_dir = os.path.join(project_root, 'GPT-SoVITS', 'GPT_SoVITS', 'pretrained_models')
    g2pw_dir = os.path.join(project_root, 'GPT-SoVITS', 'GPT_SoVITS', 'text', 'G2PWModel')

    model_checks = [
        ('s2Gv3.pth', os.path.join(pretrained_dir, 's2Gv3.pth'), 100_000_000, True),
        ('s1v3.ckpt', os.path.join(pretrained_dir, 's1v3.ckpt'), 100_000_000, True),
        ('chinese-hubert-base', os.path.join(pretrained_dir, 'chinese-hubert-base', 'pytorch_model.bin'), 100_000_000, True),
        ('BigVGAN v2 (v3 声码器)', os.path.join(pretrained_dir, 'models--nvidia--bigvgan_v2_24khz_100band_256x', 'bigvgan_generator.pt'), 100_000_000, True),
        ('SV model (ERes2NetV2)', os.path.join(pretrained_dir, 'sv', 'pretrained_eres2netv2w24s4ep4.ckpt'), 100_000_000, True),
        ('G2PW model', os.path.join(g2pw_dir, 'g2pW.onnx'), 1_000_000, False),
    ]

    for name, path, min_size, required in model_checks:
        if check_model_file(path, min_size):
            print(f"    [OK] {name}")
            results['ok'] += 1
        else:
            if required:
                print(f"    [XX] {name} - MISSING")
                results['fail'] += 1
            else:
                print(f"    [--] {name} - MISSING (optional)")
                results['warn'] += 1

    # Native Desktop (PySide6)
    if check_import(python, 'PySide6'):
        print("    [OK] PySide6 (Native Desktop)")
        results['ok'] += 1
    else:
        print("    [--] PySide6 - MISSING (Native Desktop 不可用，可用 WebUI 模式)")
        results['warn'] += 1

    # Live2D
    if check_import(python, 'live2d'):
        print("    [OK] live2d-py (Live2D 模型支持)")
        results['ok'] += 1
    else:
        print("    [--] live2d-py - MISSING (Live2D 不可用，角色不会动)")
        results['warn'] += 1

    # ChatTTS
    if check_import(python, 'ChatTTS'):
        # 检查模型是否已下载
        hf_home = os.path.join(project_root, '.cache', 'huggingface')
        chattts_snapshots = os.path.join(hf_home, 'hub', 'models--2Noise--ChatTTS', 'snapshots')
        if os.path.isdir(chattts_snapshots) and os.listdir(chattts_snapshots):
            print("    [OK] ChatTTS (已安装 + 模型已缓存)")
            results['ok'] += 1
        else:
            print("    [--] ChatTTS (已安装，模型未缓存 — 首次使用时自动下载)")
            results['warn'] += 1
    else:
        print("    [--] ChatTTS - NOT INSTALLED (对话场景 TTS 不可用)")
        results['warn'] += 1

    return results

# ================================================================
#  Main
# ================================================================

def main():
    # Determine mode
    mode = 'all'
    if '--deps' in sys.argv:
        mode = 'deps'
    elif '--models' in sys.argv:
        mode = 'models'
    elif '--verify' in sys.argv:
        mode = 'verify'

    # Find project root (this script is in scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    # Banner
    mode_labels = {
        'all': 'Full Setup (Python + Dependencies + Models)',
        'deps': 'Dependencies Only',
        'models': 'Models Only',
        'verify': 'Verification Only',
    }
    print()
    print("  ======================================================")
    print()
    print("    GuguGaga AI-VTuber - Setup")
    print(f"    Mode: {mode_labels[mode]}")
    if mode == 'all':
        print()
        print("    This will:")
        print("      1. Download embedded Python 3.11")
        print("      2. Install all Python packages")
        print("      3. Download AI model files")
        print("      4. Run verification")
        print()
        print("    All downloads use China mirror sources")
        print("    Estimated time: 20-40 minutes")
    print()
    print("  ======================================================")
    print()

    if mode == 'all':
        input("  Press Enter to start, or close to cancel...")

    # Find Python
    python = find_python(project_root)
    if python is None:
        print("  [XX] No Python found! Install Python 3.11 first:")
        print("       https://www.python.org/downloads/release/python-3119/")
        return 1
    print(f"  Using: {' '.join(python)}")

    step = 0
    totals = {'all': 6, 'deps': 3, 'models': 3, 'verify': 1}
    total = totals[mode]

    # ===== Embedded Python =====
    if mode == 'all':
        step += 1
        print_header(step, total, "Embedded Python 3.11")
        embedded_path = setup_embedded_python(project_root)
        if embedded_path:
            python = [embedded_path]  # Switch to embedded for subsequent steps

    # ===== Dependencies =====
    if mode in ('all', 'deps'):
        step += 1
        print_header(step, total, "Python Packages (Tsinghua mirror)")

        # Upgrade pip
        print("  Upgrading pip...")
        subprocess.run(
            python + ['-m', 'pip', 'install', '--upgrade', 'pip',
                      '-i', PIP_MIRROR_URL, '--trusted-host', PIP_TRUSTED],
            capture_output=True, timeout=120
        )
        print("  [OK] pip upgraded")
        print()

        # Install packages
        pkg_stats = {'ok': 0, 'skip': 0, 'fail': 0}
        for i, (imp_name, pip_spec, level) in enumerate(PACKAGES, 1):
            result = install_package(python, imp_name, pip_spec, level)
            pkg_stats[result] += 1

        print()
        print(f"  Package summary: {pkg_stats['ok']} installed, {pkg_stats['skip']} already present, {pkg_stats['fail']} failed")

        # PyTorch CUDA
        step += 1
        print_header(step, total, "PyTorch CUDA cu124 (Aliyun mirror)")
        install_pytorch_cuda(python)

        # Unlock DLLs
        print()
        unlock_dlls(project_root)

    # ===== Models =====
    if mode in ('all', 'models'):
        step += 1
        print_header(step, total, "AI Model Files")

        # For models-only mode, also set up embedded Python if needed
        if mode == 'models':
            embedded_path = setup_embedded_python(project_root)
            if embedded_path:
                python = [embedded_path]

        dl_stats = download_models(project_root)
        print()
        print(f"  Model summary: {dl_stats['ok']} downloaded, {dl_stats['skip']} already present, {dl_stats['fail']} failed")

        # ChatTTS 模型（可选，仅当 ChatTTS 已安装时下载）
        step += 1
        print_header(step, total, "ChatTTS Model (Optional)")
        chattts_stats = download_chattts_models(project_root)
        print()
        if chattts_stats['skip'] > 0:
            print("  ChatTTS: 已缓存或未安装（跳过）")
        elif chattts_stats['ok'] > 0:
            print(f"  ChatTTS: 模型下载完成")
        else:
            print("  ChatTTS: 下载失败（不影响核心功能，首次使用时将自动下载）")

    # ===== Verification =====
    step += 1
    print_header(step, total, "Final Verification")
    v = run_verification(python, project_root)

    # ===== Summary =====
    print()
    print("  ======================================================")
    if v['fail'] == 0:
        print("    SETUP COMPLETE - All checks passed!")
    else:
        print(f"    SETUP COMPLETE - {v['fail']} check(s) failed")
    print()
    print(f"    Results: [OK] {v['ok']}  [XX] {v['fail']}  [--] {v['warn']}")
    print()

    if v['fail'] == 0:
        print("    Next steps:")
        print("      1. Run scripts\\go.bat to start browser mode")
        print("      2. Enter your API key in the WebUI settings panel")
        print("      3. Start chatting!")
    else:
        print("    Some checks failed. Core features may still work.")
        print("    Missing items can be downloaded/installed manually.")
    print()
    print("  ======================================================")

    return 0 if v['fail'] == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n  Setup cancelled by user.")
        sys.exit(1)
