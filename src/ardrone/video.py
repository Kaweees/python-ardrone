"""Decode PaVE video packets from the AR.Drone into RGB image buffers."""

import struct

import av


# PaVE header format (64 bytes, little-endian packed)
# See https://developer.parrot.com/docs/SDK3/ for protocol details
_PAVE_HEADER_FMT = "<4sBBHI HH HH IIBBBBIIHBBBBxx I 12x"
_PAVE_HEADER_SIZE = struct.calcsize(_PAVE_HEADER_FMT)

# Field indices in the unpacked header tuple
_F_SIGNATURE = 0
_F_HEADER_SIZE = 2
_F_PAYLOAD_SIZE = 3


class DecodeError(Exception):
    """Raised when a video packet cannot be decoded."""


class Decoder:
    """Persistent H.264 decoder for PaVE video streams.

    Maintains codec state across calls so that P-frames can reference
    previous I-frames, matching the behavior of the original C extension.
    """

    def __init__(self):
        self._codec = av.CodecContext.create("h264", "r")

    def decode(self, data):
        """Decode a PaVE packet into an (width, height, rgb_bytes) tuple.

        Args:
            data: Raw bytes of a complete PaVE packet (header + payload).

        Returns:
            Tuple of (width, height, bytes) where bytes is RGB24 image data.

        Raises:
            DecodeError: If the packet signature is invalid, the size is
                inconsistent, or the H.264 payload cannot be decoded.
        """
        if len(data) < _PAVE_HEADER_SIZE:
            raise DecodeError("packet too short for PaVE header")

        fields = struct.unpack_from(_PAVE_HEADER_FMT, data)

        if fields[_F_SIGNATURE] != b"PaVE":
            raise DecodeError("packet did not have correct signature")

        header_size = fields[_F_HEADER_SIZE]
        payload_size = fields[_F_PAYLOAD_SIZE]

        if header_size + payload_size != len(data):
            raise DecodeError(
                "packet size did not match expected size from header"
            )

        payload = data[header_size : header_size + payload_size]

        packet = av.Packet(payload)
        try:
            frames = self._codec.decode(packet)
        except av.error.InvalidDataError as exc:
            raise DecodeError("could not decode frame") from exc

        if not frames:
            raise DecodeError("could not decode frame")

        frame = frames[0]
        rgb_frame = frame.to_rgb()
        image = bytes(rgb_frame.planes[0])
        return rgb_frame.width, rgb_frame.height, image


# Module-level decoder instance, preserving the original C extension's
# behavior of maintaining codec state across calls.
_decoder = Decoder()


def decode(data):
    """Decode a PaVE packet into an (width, height, rgb_bytes) tuple.

    This is the module-level convenience function matching the original
    C extension's ``ardrone.video.decode()`` interface.
    """
    return _decoder.decode(data)
