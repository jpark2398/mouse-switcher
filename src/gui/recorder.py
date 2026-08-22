import sys, json, hashlib, evdev, select, time

def record_device():
    # Gather all available event nodes
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    epoll = select.epoll()
    for dev in devices: 
        epoll.register(dev.fd, select.EPOLLIN)

    # 3-Second Countdown inside the process
    for i in range(3, 0, -1):
        print(f"Prepare to click in {i}...", file=sys.stderr)
        time.sleep(1)
    print("Click now!", file=sys.stderr)

    # Wait for the first event
    events = epoll.poll()
    for fd, _ in events:
        dev = next(d for d in devices if d.fd == fd)
        
        # EXACT input-remapper hashing algorithm
        caps = str(dev.capabilities(absinfo=False))
        s = caps + dev.name
        dev_hash = hashlib.md5(s.encode()).hexdigest().lower()
        
        return {
            "name": dev.name,
            "hash": dev_hash,
            "conn_id": f"{dev.info.vendor:04x}:{dev.info.product:04x}",
            "dev_id": dev.name
        }