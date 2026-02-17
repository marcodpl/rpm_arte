import json
import os
import serial_asyncio as ser
import asyncio
from dataclasses import dataclass
import time
"""
OBD-II client for polling with ELM-compatible readers.
Requires a PID pack - see pid_corsa.json
Both indexes are built at init time.
They are dictionaries- labindex has labels as keys, rxindex has rx prefixes as keys.
Both link up to PIDs.
"""
PIDPACK = "pid_corsa.json"
PORT = "/dev/rfcomm0"
BAUD = 38400


@dataclass
class SignalValue:
    value: float
    timestamp: float


class SignalCache:
    def __init__(self):
        self._data = {}

    def update(self, label, value):
        self._data[label] = SignalValue(
            value=value,
            timestamp=time.time()
        )

    def get(self, label):
        return self._data.get(label)

    def snapshot(self):
        """
        Returns a shallow copy of the entire cache.
        Safe for UI or logging reads.
        """
        return dict(self._data)


class PidIndexAndDecoder:
    def __init__(self):
        self.labindex, self.rxindex = self._buildpidindexes()

    @staticmethod
    def _buildpidindexes():
        pid = os.path.join(os.path.dirname(__file__), PIDPACK)
        with open(pid, "r") as f:
            json_pid = json.load(f)
            index, rxindex = {}, {}

            for groupname, group in json_pid["pids"].items():
                for pid in group:
                    label = pid["label"]
                    rxprefix = pid["rx"]["prefix"].upper()

                    if label in index or rxprefix in rxindex:
                        raise ValueError(f"Duplicate label/rxindex '{label}' in {PIDPACK}")

                    index[label] = pid
                    rxindex[rxprefix] = pid
            f.close()
        return index, rxindex

    def _gettxbylabel(self, label: str):
        if label not in self.labindex:
            raise ValueError(f"Unknown label '{label}' in {PIDPACK}")
        return self.labindex[label]["tx"]

    def decoderxagnostic(self, raw_rx):

        raw = raw_rx.replace(" ", "").upper()

        if raw.startswith("NO"):
            return None, None, None

        # Decodes raw message using matching prefix and formula
        for prefix, pid in self.rxindex.items():
            if raw.startswith(prefix):
                payload = raw[len(prefix):]

                values = [
                    int(payload[i:i+2], 16) for i in range(0, len(payload), 2)
                ]

                scope = {
                    name: val for name, val in zip(pid["rx"]["bytes"], values)
                }

                value = eval(pid["formula"], {}, scope)
                return pid["label"], value, pid["unit"]

        raise ValueError(f"Unknown rx prefix '{raw}' in {PIDPACK}")


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


async def tx_sender(writer, tx_queue):
    while True:
        tx = await tx_queue.get()
        writer.write((tx + "\r").encode())
        await writer.drain()


async def rx_consumer(rx_queue, pidpack: PidIndexAndDecoder, signal_cache: SignalCache, log_queue: asyncio.Queue):
    while True:
        raw = await rx_queue.get()
        label, value = pidpack.decoderxagnostic(raw)

        if label is not None:
            now = time.time()

            # Update shared cache
            signal_cache.update(label, value)

            # Enqueue log entry
            await log_queue.put((now, label, value))


async def log_writer(log_queue, filename="obd_log.csv"):
    with open(filename, "a+", buffering=1) as f:
        # CSV header (written once if file is new)
        if f.tell() == 0:
            f.write("timestamp,label,value\n")

        while True:
            timestamp, label, value = await log_queue.get()
            f.write(f"{timestamp},{label},{value}\n")


async def poller(labels, pid_index, tx_queue, interval):
    loop = asyncio.get_running_loop()

    while True:
        start = loop.time()

        for label in labels:
            tx = pid_index[label]["tx"]
            await tx_queue.put(tx)

        elapsed = loop.time() - start
        await asyncio.sleep(max(0, interval - elapsed))


async def elm_init(tx_queue):
    init_cmds = ["ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP6"]

    for cmd in init_cmds:
        await tx_queue.put(cmd)
        await asyncio.sleep(0.5)


# ============================================================
# 6. MAIN ENTRY POINT
# ============================================================

async def main():
    rx_queue = asyncio.Queue()
    tx_queue = asyncio.Queue()
    log_queue = asyncio.Queue()
    signal_cache = SignalCache()
    pidpack = PidIndexAndDecoder()

    loop = asyncio.get_running_loop()

    transport, protocol = await ser.create_serial_connection(
        loop,
        lambda: ELMProtocol(rx_queue),
        PORT,      # COMx on Windows
        baudrate=BAUD,
    )

    writer = transport

    # Core tasks
    asyncio.create_task(tx_sender(writer, tx_queue))
    asyncio.create_task(rx_consumer(rx_queue, pidpack, signal_cache, log_queue))
    asyncio.create_task(log_writer(log_queue, "obd_log.csv"))

    # Initialize ELM
    await elm_init(tx_queue)

    # Fast poller
    asyncio.create_task(
        poller(
            ["engine_rpm", "vehicle_speed"],
            pidpack.labindex,
            tx_queue,
            interval=0.1,
        )
    )

    # Slow poller
    asyncio.create_task(
        poller(
            ["engine_oil_temperature"],
            pidpack.labindex,
            tx_queue,
            interval=1.0,
        )
    )

    await asyncio.Event().wait()





