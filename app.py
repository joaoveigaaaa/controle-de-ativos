"""Entrada do sistema: python app.py usa automaticamente o ambiente do projeto."""
from pathlib import Path
import importlib.util
import os
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def bootstrap():
    environment = ROOT / '.venv'
    executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if Path(sys.prefix).resolve() != environment.resolve():
        if not executable.exists():
            print('Preparando o Python do projeto...', flush=True)
            subprocess.check_call([sys.executable, '-m', 'venv', str(environment)])
        raise SystemExit(subprocess.call([str(executable), str(ROOT / 'app.py'), *sys.argv[1:]], cwd=ROOT))
    modules = ['dotenv', 'flask', 'mysql.connector', 'waitress', 'openpyxl', 'rapidocr_onnxruntime', 'PIL']
    def available(module):
        try:
            return importlib.util.find_spec(module) is not None
        except ModuleNotFoundError:
            return False
    if not all(available(module) for module in modules):
        print('Instalando as dependências. A primeira execução precisa de internet...', flush=True)
        if not available('pip'):
            subprocess.check_call([sys.executable, '-m', 'ensurepip', '--upgrade'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt'), '--disable-pip-version-check'])


if __name__ == '__main__':
    try:
        bootstrap()
    except (subprocess.CalledProcessError, OSError) as error:
        raise SystemExit('Não foi possível preparar o ambiente. Confira sua conexão e permissão de escrita na pasta. Detalhe: ' + str(error))
    runpy.run_path(str(ROOT / 'server.py'), run_name='__main__')
else:
    from server import create_app
