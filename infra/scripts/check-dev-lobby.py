#!/usr/bin/env python3
"""Check Minecraft status and ensure direct/forged dev logins are rejected."""
import argparse
import json
import socket
import struct
import uuid


def varint(value):
    result = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        result.append(byte | (128 if value else 0))
        if not value:
            return bytes(result)


def string(value):
    data = value.encode()
    return varint(len(data)) + data


def read_varint(sock):
    value = 0
    for shift in range(0, 35, 7):
        byte = sock.recv(1)
        if not byte:
            raise RuntimeError("Unexpected connection closure")
        value |= (byte[0] & 127) << shift
        if not byte[0] & 128:
            return value
    raise RuntimeError("Invalid VarInt")


def packet(sock, payload):
    sock.sendall(varint(len(payload)) + payload)


def receive(sock):
    length = read_varint(sock)
    if length > 65536:
        raise RuntimeError("Oversized response")
    data = bytearray()
    while len(data) < length:
        part = sock.recv(length - len(data))
        if not part:
            raise RuntimeError("Truncated packet")
        data.extend(part)
    return bytes(data)


def connect(host, port, intention):
    sock = socket.create_connection((host, port), timeout=8)
    packet(sock, varint(0) + varint(767) + string(host) + struct.pack(">H", port) + varint(intention))
    return sock


def status(host, port):
    with connect(host, port, 1) as sock:
        packet(sock, b"\x00")
        data = receive(sock)
        assert data[0] == 0, "Expected status packet"
        offset = 1
        length = 0
        shift = 0
        while True:
            byte = data[offset]
            offset += 1
            length |= (byte & 127) << shift
            if not byte & 128:
                break
            shift += 7
        result = json.loads(data[offset:offset + length])
        print(f"PASS: {host}:{port} status, protocol {result['version']['protocol']}, players {result['players']['online']}")


def denied_login(host, port, forged):
    with connect(host, port, 2) as sock:
        packet(sock, b"\x00" + string("DevProbe") + uuid.uuid4().bytes)
        request = receive(sock)
        assert request == b"\x05" + string("atlas:dev_access"), "Expected dev admission cookie request"
        cookie = b"A" * 43 if forged else None
        response = b"\x04" + string("atlas:dev_access") + (b"\x00" if cookie is None else b"\x01" + varint(len(cookie)) + cookie)
        packet(sock, response)
        result = receive(sock)
        assert result[0] == 0, "Unauthorized connection progressed past login"
        assert b"Acesso negado" in result, "Expected dev access rejection"
        print(f"PASS: {'forged' if forged else 'missing'} cookie rejected before player join")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    status(args.host, 25565)
    status(args.host, 25566)
    denied_login(args.host, 25566, False)
    denied_login(args.host, 25566, True)
