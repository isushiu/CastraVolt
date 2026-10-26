import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('dev_workflow', Path('scripts/dev.py'))
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


def test_setup_generates_matching_credentials_without_overwriting_existing_env(tmp_path):
    (tmp_path / '.env.example').write_text(
        'POSTGRES_PASSWORD=replace-with-a-local-password\n'
        'CASTRAVOLT_DATABASE_URL=postgresql+psycopg://castravolt:replace-with-a-local-password@127.0.0.1:5432/castravolt\n')
    dev.prepare_env(tmp_path)
    original = (tmp_path / '.env').read_text()
    password = next(line.split('=',1)[1] for line in original.splitlines() if line.startswith('POSTGRES_PASSWORD='))
    assert password != 'replace-with-a-local-password'
    assert len(password) >= 32 and f':{password}@' in original
    dev.prepare_env(tmp_path)
    assert (tmp_path / '.env').read_text() == original


def test_generated_env_is_not_written_when_example_missing(tmp_path):
    import pytest
    with pytest.raises(dev.WorkflowError):
        dev.prepare_env(tmp_path)
    assert not (tmp_path / '.env').exists()


def test_environment_password_is_not_replaced_in_existing_user_config(tmp_path):
    (tmp_path / '.env').write_text('CUSTOM_SETTING=keep-me\n')
    dev.prepare_env(tmp_path)
    assert (tmp_path / '.env').read_text() == 'CUSTOM_SETTING=keep-me\n'


def test_command_failure_stops_workflow(monkeypatch):
    import pytest
    import subprocess
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ['test'])
    monkeypatch.setattr(dev.subprocess,'run',fail)
    with pytest.raises(dev.WorkflowError):
        dev.run(['test'], Path('.'))


def test_url_readiness_rejects_wrong_service(monkeypatch):
    import io
    monkeypatch.setattr(dev.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(b'{"status":"alive"}'))
    assert dev.check_api('http://local') is False


def test_setup_installs_locked_dependencies_in_order(tmp_path, monkeypatch):
    (tmp_path/'.env').write_text('CUSTOM_SETTING=keep\n')
    commands = []
    monkeypatch.setattr(dev,'require_tools',lambda names: None)
    monkeypatch.setattr(dev,'ensure_port_available',lambda port: None)
    monkeypatch.setattr(dev,'run',lambda command, root: commands.append(command))
    dev.setup(tmp_path)
    assert commands[0] == ['uv','sync','--locked','--group','model-validation']
    assert commands[1][1:5] == ['ci','--prefix','frontend','--no-audit']


def test_setup_rejects_active_services_before_touching_dependencies(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(dev,'require_tools',lambda names: None)
    def busy(port): raise dev.WorkflowError('Stop the existing preview')
    monkeypatch.setattr(dev,'ensure_port_available',busy)
    monkeypatch.setattr(dev,'run',lambda *a, **k: pytest.fail('Must not install while running'))
    with pytest.raises(dev.WorkflowError,match='existing preview'):
        dev.setup(tmp_path)


def test_root_follows_relocated_script_with_spaces(tmp_path):
    import runpy
    root = tmp_path/'another computer'/'project with spaces'
    scripts = root/'scripts'
    scripts.mkdir(parents=True)
    copied = scripts/'dev.py'
    copied.write_text(Path('scripts/dev.py').read_text(encoding='utf-8'),encoding='utf-8')
    loaded = runpy.run_path(str(copied),run_name='portable_import')
    assert loaded['ROOT'] == root.resolve()
    loaded['prepare_env'].__globals__['ROOT'] = root
    assert not (root/'.env').exists()


def test_failed_migration_stops_only_database_started_by_this_run(tmp_path, monkeypatch):
    import pytest
    import types
    python = tmp_path/'.venv'/('Scripts/python.exe' if dev.os.name=='nt' else 'bin/python')
    python.parent.mkdir(parents=True); python.touch()
    (tmp_path/'frontend/node_modules').mkdir(parents=True)
    (tmp_path/'.env').touch()
    monkeypatch.setattr(dev,'require_tools',lambda names: None)
    monkeypatch.setattr(dev,'ensure_port_available',lambda port: None)
    stopped = []
    monkeypatch.setattr(dev.subprocess,'run',lambda command, **kw: stopped.append(command))
    for running in ['', 'db\n']:
        def fake_run(command, root, **kwargs):
            if 'ps' in command:
                return types.SimpleNamespace(stdout=running)
            if 'alembic' in command:
                raise dev.WorkflowError('Migration failed')
            return types.SimpleNamespace()
        monkeypatch.setattr(dev,'run',fake_run)
        stopped.clear()
        with pytest.raises(dev.WorkflowError,match='Migration failed'):
            dev.start(tmp_path)
        assert bool(stopped) == (not running)
        if stopped: assert stopped == [['docker','compose','stop','db']]


def test_windows_cleanup_kills_descendants_after_launcher_exits(tmp_path):
    import ctypes
    from ctypes import wintypes
    import sys
    import pytest
    if dev.os.name != 'nt': pytest.skip('Windows job ownership check')
    script = tmp_path/'launcher.py'
    pidfile = tmp_path/'child.pid'
    script.write_text("import subprocess,sys\nfrom pathlib import Path\n"
                      "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
                      "Path(sys.argv[1]).write_text(str(child.pid))\n")
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    with (tmp_path/'log').open('w') as log:
        process = dev.launch([sys.executable,str(script),str(pidfile)],tmp_path,log)
        handle = None
        try:
            process.wait(timeout=15)
            handle = kernel.OpenProcess(0x100000,False,int(pidfile.read_text()))
            assert handle and kernel.WaitForSingleObject(handle,0) == 258
            dev.stop_child(process)
            assert kernel.WaitForSingleObject(handle,5000) == 0
        finally:
            dev.stop_child(process)
            if handle: kernel.CloseHandle(handle)
