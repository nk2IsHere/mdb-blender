import datetime

global G_DEBUG
global G_DEPTH


def setDepth(depth: int):
    global G_DEPTH
    G_DEPTH = int(depth)


def increaseDepth():
    global G_DEPTH
    G_DEPTH += 1


def decreaseDepth():
    global G_DEPTH
    G_DEPTH -= 1


def setDebug(debug: bool):
    global G_DEBUG
    G_DEBUG = bool(debug)


def debugPrint(*args, **kwargs):
    global G_DEBUG
    global G_DEPTH
    if G_DEBUG:
        currentTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")
        print(
            f"[{currentTime[:-3]}] ",
            '--' * G_DEPTH + ('> ' if G_DEPTH > 0 else ''),
            ', '.join(map(lambda arg: str(arg), args)) if len(args) > 0 else '',
            ' | ' if len(args) > 0 and len(kwargs) > 0 else '',
            ' '.join([f'{key}: {value},' for key, value in kwargs.items()])[:-1] if len(kwargs) > 0 else '',
            sep=''
        )
