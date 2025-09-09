import os


MODEL_PATH = os.environ.get('MODEL_PATH')
N_THREADS = int(os.environ.get('N_THREADS', '8'))
CTX = int(os.environ.get('CTX', '2048'))
TEMP = float(os.environ.get('TEMP', '0.0'))
MAX_TOKENS = int(os.environ.get('MAX_TOKENS', '512'))
