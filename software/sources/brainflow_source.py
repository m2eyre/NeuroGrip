"""Any BrainFlow-supported board: OpenBCI Cyton/Ganglion, Muse 2/S, Neurosity,
g.tec Unicorn, BrainBit, and a built-in synthetic board for testing.

    pip install brainflow
    python neurogrip_bridge.py --source sources/brainflow_source.py

Pick the board with environment variables (or edit the defaults below):

    NG_BF_BOARD   board name from BoardIds, e.g. SYNTHETIC_BOARD, CYTON_BOARD,
                  GANGLION_BOARD, MUSE_2_BOARD, MUSE_S_BOARD, UNICORN_BOARD
    NG_BF_SERIAL  serial port, for boards with a USB dongle (Cyton, Ganglion)
    NG_BF_MAC     MAC address, for some Bluetooth boards (optional)

Examples (Windows PowerShell):   $env:NG_BF_BOARD="CYTON_BOARD"; $env:NG_BF_SERIAL="COM4"
         (Mac/Linux):            NG_BF_BOARD=MUSE_2_BOARD python neurogrip_bridge.py --source ...

BrainFlow returns EEG in microvolts, so the default clench mode works as-is.
Board list: https://brainflow.readthedocs.io/en/stable/SupportedBoards.html
"""
import os

import numpy as np

BOARD = os.environ.get("NG_BF_BOARD", "SYNTHETIC_BOARD")
SERIAL = os.environ.get("NG_BF_SERIAL", "")
MAC = os.environ.get("NG_BF_MAC", "")


class BrainFlowSource:
    def __init__(self, board_name, max_ch=8):
        from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

        board_id = BoardIds[board_name].value
        params = BrainFlowInputParams()
        params.serial_port, params.mac_address = SERIAL, MAC
        self.board = BoardShim(board_id, params)
        self.board.prepare_session()
        self.board.start_stream()
        self.eeg_rows = BoardShim.get_eeg_channels(board_id)[:max_ch]
        self.fs = float(BoardShim.get_sampling_rate(board_id))
        self.n_ch = len(self.eeg_rows)
        try:
            names = BoardShim.get_eeg_names(board_id)[: self.n_ch]
        except Exception:
            names = []
        self.labels = names if len(names) == self.n_ch else [f"ch{i + 1}" for i in range(self.n_ch)]
        print(f"BrainFlow {board_name}: {self.n_ch} EEG ch @ {self.fs:.0f} Hz")

    def read(self):
        data = self.board.get_board_data()           # (rows, samples), clears the buffer
        if data.shape[1] == 0:
            return np.empty((0, self.n_ch))
        return data[self.eeg_rows].T

    def __del__(self):
        try:
            self.board.stop_stream()
            self.board.release_session()
        except Exception:
            pass


def make_source(args):
    return BrainFlowSource(BOARD, args.channels or 8)
