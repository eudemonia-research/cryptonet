import traceback

def debug(*msgs):
    print(*msgs)

def print_traceback():
    traceback.print_stack()