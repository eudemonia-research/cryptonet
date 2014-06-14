import traceback


def debug(*msgs):
    print(*msgs)

def verbose_debug(*msgs):
    #print(*msgs)
    pass

def print_traceback():
    traceback.print_stack()