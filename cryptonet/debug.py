import traceback

DEBUG_ON = False

def enable_debug():
    global DEBUG_ON
    DEBUG_ON = True

def debug(*msgs):
    global DEBUG_ON
    if DEBUG_ON:
        print(*msgs)

def verbose_debug(*msgs):
    #print(*msgs)
    pass

def print_traceback():
    traceback.print_stack()