import os
import logging

def custom_logger(name: str, file_path: str = None, level: int = logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logging.getLogger().setLevel(logging.WARNING)

    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [pid=%(process)d] %(name)s: %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'log')
    os.makedirs(log_dir, exist_ok=True)

    if file_path is None:
        file_path = os.path.join(log_dir, 'log.log')

    file_handler = logging.FileHandler(file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger