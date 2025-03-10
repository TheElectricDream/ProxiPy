import os, time, ctypes, multiprocessing

def timing_task():
    # Attempt to set real-time scheduling (SCHED_FIFO)
    libc = ctypes.CDLL("libc.so.6")
    SCHED_FIFO = 1
    class sched_param(ctypes.Structure):
        _fields_ = [("sched_priority", ctypes.c_int)]
    param = sched_param()
    param.sched_priority = 99  # Use a high priority
    if libc.sched_setscheduler(0, SCHED_FIFO, ctypes.byref(param)) != 0:
        print("Warning: Could not set real-time scheduler.")
    
    # Your timing-critical loop
    while True:
        cycle_start = time.perf_counter()
        # Do your work here...
        # Wait until the next cycle
        time.sleep(0.2)  # Replace with your precise delay mechanism
        cycle_end = time.perf_counter()
        print(f"Cycle took {cycle_end - cycle_start:.6f} s")

if __name__ == '__main__':
    p = multiprocessing.Process(target=timing_task)
    p.start()
    p.join()
