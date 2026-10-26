"""Local setup and supervised development startup. Standard-library only."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SETUP_COMMAND = '.\\setup.cmd' if os.name == 'nt' else 'sh setup.sh'
START_COMMAND = '.\\start.cmd' if os.name == 'nt' else 'sh start.sh'


class WorkflowError(Exception):
    pass


def run(command, root, **kwargs):
    try:
        return subprocess.run(command, cwd=root, check=True, **kwargs)
    except (subprocess.CalledProcessError, OSError) as exc:
        raise WorkflowError(f'Command failed: {command[0]}. Resolve the error above and retry.') from exc


def require_tools(names):
    missing = [name for name in names if not shutil.which(name)]
    if missing:
        help_links = {'uv':'uv: https://docs.astral.sh/uv/getting-started/installation/',
                      'node':'Node.js 22.12+: https://nodejs.org/en/download',
                      'npm':'Node.js (includes npm): https://nodejs.org/en/download',
                      'npm.cmd':'Node.js (includes npm): https://nodejs.org/en/download',
                      'docker':'Docker Desktop: https://www.docker.com/products/docker-desktop/'}
        raise WorkflowError('Missing prerequisites:\n' + '\n'.join(help_links.get(name,name) for name in missing)
                            + '\nAfter installing, reopen the terminal and retry.')


def check_prerequisites(root=ROOT, engine_required=False):
    npm = 'npm.cmd' if os.name == 'nt' else 'npm'
    require_tools(['uv','node',npm,'docker'])
    import re
    version = run(['node','--version'],root,capture_output=True,text=True).stdout.strip()
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',version)
    if not match or tuple(map(int,match.groups())) < (22,12,0):
        raise WorkflowError('Node.js 22.12 or newer is required. Update from https://nodejs.org/en/download')
    try:
        run(['docker','compose','version'],root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
    except (WorkflowError,subprocess.TimeoutExpired) as exc:
        raise WorkflowError('Docker is installed, but Docker Compose is missing/unavailable. Install or update Docker Desktop (or the Compose plugin on Linux).') from exc
    print(f'Prerequisites found: uv, Node.js {version}, npm and Docker Compose.',flush=True)
    try:
        run(['docker','info'],root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
    except (WorkflowError,subprocess.TimeoutExpired) as exc:
        message = ('Docker is installed but its engine is not accessible. Open Docker Desktop and wait until it says the engine is running. '
                   'If Docker Desktop shows a WSL/virtualisation or permissions error, resolve that message first. '
                   'On Linux, start Docker Engine and ensure your account can access it.')
        if engine_required: raise WorkflowError(message) from exc
        print('Note: '+message+'\nDependency setup can continue; starting the app will require Docker.',flush=True)
        return False
    print('Docker engine is ready.',flush=True)
    return True


def prepare_env(root):
    path = root / '.env'
    if path.exists():
        print('Keeping your existing .env unchanged.', flush=True)
        return
    example = root / '.env.example'
    if not example.is_file():
        raise WorkflowError('.env.example is missing. Run from the complete project checkout.')
    content = example.read_text(encoding='utf-8-sig')
    content = content.replace('replace-with-a-local-password', secrets.token_hex(24))
    content = '# Generated local configuration. Do not commit this file.\n' + content
    # Never overwrite a file created by another concurrent setup process.
    try:
        with path.open('x', encoding='utf-8') as handle:
            handle.write(content)
        if os.name != 'nt':
            path.chmod(0o600)
    except FileExistsError:
        return
    print('Created .env with a matching random local database password.', flush=True)


def setup(root=ROOT):
    npm = 'npm.cmd' if os.name == 'nt' else 'npm'
    check_prerequisites(root)
    # Windows cannot replace binaries used by active preview/API processes.
    for port in (8000, 5173):
        ensure_port_available(port)
    print('1/3 Preparing local configuration…', flush=True)
    prepare_env(root)
    print('2/3 Installing locked backend dependencies…', flush=True)
    run(['uv', 'sync', '--locked', '--group', 'model-validation'], root)
    print('3/3 Installing locked frontend dependencies…', flush=True)
    try:
        run([npm, 'ci', '--prefix', 'frontend', '--no-audit', '--no-fund'], root)
    except WorkflowError as exc:
        raise WorkflowError(f'Frontend installation failed. On Windows, an older Vite/esbuild process may hold files open. Stop this project\'s running preview (Ctrl+C), then rerun {SETUP_COMMAND}. Administrator access is normally unnecessary.') from exc
    print(f'\nSetup complete. Start Docker, then run {START_COMMAND}', flush=True)


def ensure_port_available(port):
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', port))
        except OSError as exc:
            raise WorkflowError(f'Port {port} is already in use. Stop the existing preview/server, then retry.') from exc


def check_api(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = json.load(response)
        return body.get('name') == 'CastraVolt' and body.get('stage') == 'foundation'
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False


def check_frontend(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200 and 'CastraVolt' in response.read().decode('utf-8')
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def launch(command, root, log):
    job = WindowsJob() if os.name == 'nt' else None
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    try:
        process = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, **options)
        if job:
            try:
                job.assign(process)
            except Exception:
                process.kill(); process.wait()
                raise
        process._castravolt_job = job
        return process
    except Exception:
        if job: job.close()
        raise


class WindowsJob:
    """Own the entire child process tree, including descendants of exited launchers."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),
                        ('flags',w.DWORD),('min_working_set',ctypes.c_size_t),('max_working_set',ctypes.c_size_t),
                        ('active_processes',w.DWORD),('affinity',ctypes.c_size_t),
                        ('priority',w.DWORD),('scheduling',w.DWORD)]
        class Limits(ctypes.Structure):
            _fields_ = [('basic',Basic),('io_counters',ctypes.c_ulonglong*6),
                        ('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
                        ('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]
        self.kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p,w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE,w.HANDLE]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None,None)
        if not self.handle: raise ctypes.WinError(ctypes.get_last_error())
        limits = Limits(); limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
            error = ctypes.get_last_error(); self.close(); raise ctypes.WinError(error)

    def assign(self,process):
        if not self.kernel.AssignProcessToJobObject(self.handle,int(process._handle)):
            import ctypes
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def stop_child(process):
    job = getattr(process,'_castravolt_job',None)
    if job:
        job.close()  # closes descendants even if their original launcher has exited
    elif os.name == 'nt' and process.poll() is None:
        # Only the specific process tree launched by this invocation is stopped.
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    elif os.name != 'nt':
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def wait_for_service(process, check, label, log_path, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise WorkflowError(f'{label} stopped unexpectedly. See {log_path}')
        if check():
            return
        time.sleep(0.3)
    raise WorkflowError(f'{label} did not become ready. See {log_path}')


def start(root=ROOT):
    check_prerequisites(root,engine_required=True)
    python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists() or not (root/'frontend/node_modules').exists() or not (root/'.env').exists():
        raise WorkflowError(f'First run {SETUP_COMMAND} to prepare this project.')
    ensure_port_available(8000)
    ensure_port_available(5173)
    print('Using project virtual environment: .venv',flush=True)
    running = run(['docker','compose','ps','--status','running','--services'],root,capture_output=True,text=True).stdout.splitlines()
    started_database = 'db' not in running
    if started_database:
        config = run(['docker','compose','config','--format','json'],root,capture_output=True,text=True)
        published = json.loads(config.stdout)['services']['db']['ports'][0]['published']
        try:
            ensure_port_available(int(published))
        except WorkflowError as exc:
            raise WorkflowError(f'Database port {published} is occupied or blocked. Choose an available POSTGRES_PORT in .env and use the same port in CASTRAVOLT_DATABASE_URL. The PostgreSQL port inside Docker remains 5432.') from exc
    processes, logs = [], []
    try:
        print('1/4 Starting PostgreSQL and waiting for readiness…',flush=True)
        run(['docker','compose','up','-d','db','--wait','--wait-timeout','90'],root)
        print('2/4 Applying database migrations…',flush=True)
        run([str(python),'-m','alembic','upgrade','head'],root)
        log_dir = root/'tmp'
        log_dir.mkdir(exist_ok=True)
        for label,command,check in [
            ('backend',[str(python),'-m','uvicorn','castravolt.main:app','--host','127.0.0.1','--port','8000'],
             lambda: check_api('http://127.0.0.1:8000/api/v1/system')),
            ('frontend',['node',str(root/'frontend/node_modules/vite/bin/vite.js'),
                         '--host','127.0.0.1','--port','5173'],
             lambda: check_frontend('http://127.0.0.1:5173/')),
        ]:
            print(f'{3 if label=="backend" else 4}/4 Starting {label}…',flush=True)
            log_path = log_dir / f'dev-{label}.log'
            log = log_path.open('w',encoding='utf-8'); logs.append(log)
            service_root = root/'frontend' if label == 'frontend' else root
            process = launch(command,service_root,log); processes.append(process)
            wait_for_service(process,check,label,log_path)
        # Migration success isn't a replacement for checking the running API's DB connection.
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=5) as response:
                ready = json.load(response)
            if ready.get('database') != 'connected':
                raise ValueError('Database unavailable')
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise WorkflowError('The API cannot reach PostgreSQL. Check .env and tmp/dev-backend.log.') from exc
        print('\nCastraVolt is running: http://127.0.0.1:5173/\nKeep this terminal open. Press Ctrl+C to stop.\nLogs: tmp/dev-backend.log and tmp/dev-frontend.log',flush=True)
        while True:
            if any(process.poll() is not None for process in processes):
                raise WorkflowError('An app service stopped. Check the logs in tmp/ and restart.')
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\nStopping CastraVolt…',flush=True)
    finally:
        for process in reversed(processes):
            stop_child(process)
        for log in logs:
            log.close()
        if started_database:
            # Keep existing shared DB services running; stop only one started here.
            subprocess.run(['docker','compose','stop','db'],cwd=root,check=False)
        print('App services stopped. Database data has been kept.',flush=True)


def main():
    parser = argparse.ArgumentParser(description='CastraVolt local development')
    parser.add_argument('action', choices=['setup','start','check'])
    args = parser.parse_args()
    try:
        if args.action == 'check':
            check_prerequisites(engine_required=True)
        else:
            (setup if args.action == 'setup' else start)()
    except WorkflowError as exc:
        print(f'\n{exc}',file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nCancelled.',file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    sys.exit(main())
