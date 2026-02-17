import asyncio
import json
from token import COMMA

import serial_asyncio
import time
from dataclasses import dataclass
from typing import Callable, List
import os


PIDPACKLOC = "pid_corsa.json"
COM = "/dev/rfcomm0"
BAUD = 38400
# ============================================================
# 1. PID PACK (normally loaded from JSON)
# ============================================================
def load_pid_pack(filename):
    pid = os.path.join(os.path.dirname(__file__), PIDPACKLOC)
    with open(pid, "r") as f:
        return json.load(f)


PID_PACK = load_pid_pack(PIDPACKLOC)
# ============================================================
# 2. PID INDEX BUILDERS
# ============================================================
def build_pid_index(pid_pack):
    index = {}
    for group in pid_pack["pids"].values():
        for pid in group:
            label = pid["label"]
            if label in index:
                raise ValueError(f"Duplicate PID label: {label}")
            index[label] = pid
    return index


def build_rx_prefix_index(pid_pack):
    index = {}
    for group in pid_pack["pids"].values():
        for pid in group:
            prefix = pid["rx"]["expected_prefix"].upper()
            if prefix in index:
                raise ValueError(f"Duplicate RX prefix: {prefix}")
            index[prefix] = pid
    return index


PID_INDEX = build_pid_index(PID_PACK)
RX_INDEX = build_rx_prefix_index(PID_PACK)

# ============================================================
# 3. RX-AGNOSTIC DECODER
# ============================================================

def decode_rx_agnostic(raw_rx, rx_index):
    raw = raw_rx.replace(" ", "").upper()

    if not raw or raw.startswith("NO"):
        return None, None

    for prefix, pid in rx_index.items():
        if raw.startswith(prefix):
            payload = raw[len(prefix):]

            values = [
                int(payload[i:i + 2], 16)
                for i in range(0, len(payload), 2)
            ]

            scope = {
                name: val
                for name, val in zip(pid["rx"]["bytes"], values)
            }

            value = eval(pid["formula"], {}, scope)
            return pid["label"], value

    return None, None

# ============================================================
# 4. SHARED SIGNAL CACHE
# ============================================================

@dataclass
class SignalValue:
    value: float
    timestamp: float


class SignalCache:
    def __init__(self):
        self._data = {}

    def update(self, label, value):
        self._data[label] = SignalValue(value, time.time())

    def get(self, label):
        return self._data.get(label)

    def snapshot(self):
        return dict(self._data)

# ============================================================
# 5. DERIVED SIGNALS
# ============================================================

@dataclass
class DerivedSignal:
    label: str
    dependencies: List[str]
    compute: Callable[[dict], float]
    unit: str


class DerivedSignalEngine:
    def __init__(self, signal_cache, derived_signals, log_queue):
        self.signal_cache = signal_cache
        self.derived_signals = derived_signals
        self.log_queue = log_queue

    async def update(self):
        snapshot = self.signal_cache.snapshot()
        now = time.time()

        for ds in self.derived_signals:
            if not all(dep in snapshot for dep in ds.dependencies):
                continue

            try:
                value = ds.compute(snapshot)
            except Exception:
                continue

            self.signal_cache.update(ds.label, value)
            await self.log_queue.put((now, ds.label, value))

# ---- Derived signal implementations ----

def compute_engine_power(cache):
    rpm = cache["engine_rpm"].value
    torque = cache["engine_torque_estimate"].value
    return (torque * rpm) / 9549


def compute_vehicle_acceleration(cache):
    speed = cache["vehicle_speed"]

    prev = getattr(speed, "prev", None)
    if prev is None:
        speed.prev = speed
        return 0.0

    dv = (speed.value - prev.value) / 3.6
    dt = speed.timestamp - prev.timestamp
    speed.prev = speed

    if dt <= 0:
        return 0.0

    return dv / dt


DERIVED_SIGNALS = [
    DerivedSignal(
        label="engine_power_estimate",
        dependencies=["engine_rpm", "engine_torque_estimate"],
        compute=compute_engine_power,
        unit="kW",
    ),
    DerivedSignal(
        label="vehicle_acceleration",
        dependencies=["vehicle_speed"],
        compute=compute_vehicle_acceleration,
        unit="m/s²",
    ),
]

# ============================================================
# 6. ASYNC LOGBOOK
# ============================================================

async def log_writer(log_queue, filename="obd_log.csv"):
    with open(filename, "a", buffering=1) as f:
        if f.tell() == 0:
            f.write("timestamp,label,value\n")

        while True:
            ts, label, value = await log_queue.get()
            f.write(f"{ts},{label},{value}\n")

# ============================================================
# 7. ASYNC SERIAL PROTOCOL
# ============================================================

class ELMProtocol(asyncio.Protocol):
    def __init__(self, rx_queue):
        self.rx_queue = rx_queue
        self.buffer = ""

    def data_received(self, data):
        self.buffer += data.decode(errors="ignore")

        while "\r" in self.buffer:
            line, self.buffer = self.buffer.split("\r", 1)
            line = line.strip()
            if line:
                asyncio.create_task(self.rx_queue.put(line))

# ============================================================
# 8. ASYNC TASKS
# ============================================================

async def tx_sender(writer, tx_queue):
    while True:
        tx = await tx_queue.get()
        writer.write((tx + "\r").encode())
        await writer.drain()


async def rx_consumer(rx_queue, rx_index, signal_cache, log_queue, derived_engine):
    while True:
        raw = await rx_queue.get()
        label, value = decode_rx_agnostic(raw, rx_index)

        if label is not None:
            signal_cache.update(label, value)
            await log_queue.put((time.time(), label, value))
            await derived_engine.update()

# ============================================================
# 8b. ASYNC POLLER
# ============================================================

class PollingState:
    def __init__(self):
        self._groups = {}
        self._lock = asyncio.Lock()

    async def set(self, interval, labels):
        """
        Replace the entire polling set for an interval.
        """
        async with self._lock:
            self._groups[interval] = set(labels)

    async def add(self, interval, labels):
        """
        Append labels to the polling set for an interval.
        """
        async with self._lock:
            if interval not in self._groups:
                self._groups[interval] = set()
            self._groups[interval].update(labels)

    async def remove(self, interval, labels):
        """
        Remove labels from the polling set for an interval.
        """
        async with self._lock:
            if interval in self._groups:
                self._groups[interval].difference_update(labels)

    async def get(self, interval):
        """
        Get current labels for an interval.
        """
        async with self._lock:
            return set(self._groups.get(interval, []))

async def adaptive_poller(interval, polling_state, pid_index, tx_queue):
    loop = asyncio.get_running_loop()

    while True:
        start = loop.time()

        labels = await polling_state.get(interval)

        for label in labels:
            await tx_queue.put(pid_index[label]["tx"])

        elapsed = loop.time() - start
        await asyncio.sleep(max(0, interval - elapsed))



async def elm_init(tx_queue):
    for cmd in ["ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP6"]:
        await tx_queue.put(cmd)
        await asyncio.sleep(0.5)

# ============================================================
# 9. MAIN ENTRY POINT
# ============================================================

async def main():
    rx_queue = asyncio.Queue()
    tx_queue = asyncio.Queue()
    log_queue = asyncio.Queue()
    polling_state = PollingState()

    signal_cache = SignalCache()
    derived_engine = DerivedSignalEngine(
        signal_cache, DERIVED_SIGNALS, log_queue
    )

    loop = asyncio.get_running_loop()

    transport, protocol = await serial_asyncio.create_serial_connection(
        loop,
        lambda: ELMProtocol(rx_queue),
        COM,   # COMx on Windows
        baudrate=BAUD,
    )

    writer = transport

    asyncio.create_task(tx_sender(writer, tx_queue))
    asyncio.create_task(rx_consumer(
        rx_queue, RX_INDEX, signal_cache, log_queue, derived_engine
    ))
    asyncio.create_task(log_writer(log_queue))

    await elm_init(tx_queue)

    asyncio.create_task(
        adaptive_poller(
            0.1,
            polling_state,
            PID_INDEX,
            tx_queue
        )
    )

    asyncio.create_task(
        adaptive_poller(
            1.0,
            polling_state,
            PID_INDEX,
            tx_queue
        )
    )

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
