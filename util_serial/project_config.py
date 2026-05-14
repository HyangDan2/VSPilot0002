"""
Project and port configuration helpers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class SerialPortConfig:
    enabled: bool = True
    port_no: int = 1
    alias: str = ""
    device: str = ""
    baudrate: int = 9600
    data_bits: int = 8
    parity: str = "None"
    stop_bits: float = 1.0
    timeout_ms: int = 1000
    write_timeout_ms: int = 1000
    encoding: str = "utf-8"
    line_ending: str = "CRLF"
    flow_control: str = "None"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SerialPortConfig":
        return cls(
            enabled=bool(data.get("enabled", True)),
            port_no=int(data.get("port_no", 1)),
            alias=str(data.get("alias", "")),
            device=str(data.get("device", "")),
            baudrate=int(data.get("baudrate", 9600)),
            data_bits=int(data.get("data_bits", 8)),
            parity=str(data.get("parity", "None")),
            stop_bits=float(data.get("stop_bits", 1.0)),
            timeout_ms=int(data.get("timeout_ms", 1000)),
            write_timeout_ms=int(data.get("write_timeout_ms", 1000)),
            encoding=str(data.get("encoding", "utf-8")),
            line_ending=str(data.get("line_ending", "CRLF")),
            flow_control=str(data.get("flow_control", "None")),
        )


@dataclass
class ProjectConfig:
    ui: Dict[str, Any] = field(default_factory=dict)
    ports: List[SerialPortConfig] = field(default_factory=list)
    commands: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def default(cls) -> "ProjectConfig":
        return cls(
            ui={"width": 1600, "height": 900, "splitter_sizes": [640, 640, 320]},
            ports=[SerialPortConfig(port_no=1)],
            commands=[
                {
                    "enabled": True,
                    "command_no": 1,
                    "port_no": 1,
                    "command": "",
                    "wait_time_ms": 0,
                    "next_command_no": "",
                    "timeout_ms": 1000,
                    "memo": "",
                }
            ],
        )

    @classmethod
    def load(cls, path: Path) -> "ProjectConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        ports = [SerialPortConfig.from_dict(item) for item in data.get("ports", [])]
        commands = list(data.get("commands", []))
        ui = dict(data.get("ui", {}))
        return cls(ui=ui, ports=ports, commands=commands)

    def save(self, path: Path) -> None:
        payload = {
            "ui": self.ui,
            "ports": [asdict(config) for config in self.ports],
            "commands": self.commands,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
