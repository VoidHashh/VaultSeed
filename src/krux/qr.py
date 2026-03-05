# The MIT License (MIT)

# Copyright (c) 2021-2024 Krux contributors

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# pylint: disable=E1101
import io
import math
import qrcode

FORMAT_NONE = 0
FORMAT_PMOFN = 1
FORMAT_BBQR = 3

PMOFN_PREFIX_LENGTH_1D = 6
PMOFN_PREFIX_LENGTH_2D = 8
BBQR_PREFIX_LENGTH = 8

# https://www.qrcode.com/en/about/version.html
QR_CAPACITY_NUMERIC = [41,77,127,187,255,322,370,461,552,652,772,883,1022,1101,1250,1408,1548,1725,1903,2061]
QR_CAPACITY_ALPHANUMERIC = [25,47,77,114,154,195,224,279,335,395,468,535,619,667,758,854,938,1046,1153,1249]
QR_CAPACITY_BYTE = [17,32,53,78,106,134,154,192,230,271,321,367,425,458,520,586,644,718,792,858]


class QRPartParser:
    """Responsible for parsing either a singular or animated series of QR codes
    and returning the final decoded, combined data
    """

    def __init__(self):
        self.parts = {}
        self.total = -1
        self.format = None
        self.bbqr = None

    def parsed_count(self):
        return len(self.parts)

    def processed_parts_count(self):
        return len(self.parts)

    def total_count(self):
        return self.total

    def parse(self, data):
        if self.format is None:
            self.format, self.bbqr = detect_format(data)

        if self.format == FORMAT_NONE:
            self.parts[1] = data
            self.total = 1
        elif self.format == FORMAT_PMOFN:
            part, index, total = parse_pmofn_qr_part(data)
            self.parts[index] = part
            self.total = total
            return index - 1
        elif self.format == FORMAT_BBQR:
            from .bbqr import parse_bbqr
            part, index, total = parse_bbqr(data)
            self.parts[index] = part
            self.total = total
            return index
        return None

    def is_complete(self):
        keys_check = (
            sum(range(1, self.total + 1))
            if self.format in (FORMAT_PMOFN, FORMAT_NONE)
            else sum(range(self.total))
        )
        return (
            self.total != -1
            and self.parsed_count() == self.total_count()
            and sum(self.parts.keys()) == keys_check
        )

    def result(self):
        if self.format == FORMAT_BBQR:
            from .bbqr import decode_bbqr
            return decode_bbqr(self.parts, self.bbqr.encoding, self.bbqr.file_type)

        code_buffer = io.StringIO("")
        for _, part in sorted(self.parts.items()):
            if isinstance(part, bytes):
                return part
            code_buffer.write(part)
        code = code_buffer.getvalue()
        code_buffer.close()
        return code


def to_qr_codes(data, max_width, qr_format):
    if qr_format == FORMAT_NONE:
        code = qrcode.encode(data)
        yield (code, 1)
    else:
        num_parts, part_size = find_min_num_parts(data, max_width, qr_format)
        if qr_format == FORMAT_PMOFN:
            part_index = 0
            while True:
                part_number = "p%dof%d " % (part_index + 1, num_parts)
                if isinstance(data, bytes):
                    part_number = part_number.encode()
                if part_index == num_parts - 1:
                    part = part_number + data[part_index * part_size :]
                    part_index = 0
                else:
                    part = part_number + data[part_index * part_size : (part_index + 1) * part_size]
                    part_index += 1
                code = qrcode.encode(part)
                yield (code, num_parts)
        elif qr_format == FORMAT_BBQR:
            from .bbqr import int2base36
            part_index = 0
            while True:
                header = "B$%s%s%s%s" % (data.encoding, data.file_type, int2base36(num_parts), int2base36(part_index))
                if part_index == num_parts - 1:
                    part = header + data.payload[part_index * part_size :]
                    part_index = 0
                else:
                    part = header + data.payload[part_index * part_size : (part_index + 1) * part_size]
                    part_index += 1
                code = qrcode.encode(part)
                yield (code, num_parts)


def get_size(qr_code):
    size = math.sqrt(len(qr_code) * 8)
    return int(size)


def max_qr_bytes(max_width, encoding="byte"):
    max_width -= 2
    qr_version = (max_width - 17) // 4
    if encoding == "alphanumeric":
        capacity_list = QR_CAPACITY_ALPHANUMERIC
    else:
        capacity_list = QR_CAPACITY_BYTE
    try:
        return capacity_list[qr_version - 1]
    except:
        return capacity_list[-1]


def find_min_num_parts(data, max_width, qr_format):
    encoding = "alphanumeric" if qr_format == FORMAT_BBQR else "byte"
    qr_capacity = max_qr_bytes(max_width, encoding)
    if qr_format == FORMAT_PMOFN:
        data_length = len(data)
        part_size = qr_capacity - PMOFN_PREFIX_LENGTH_1D
        num_parts = (data_length + part_size - 1) // part_size
        if num_parts > 9:
            part_size = qr_capacity - PMOFN_PREFIX_LENGTH_2D
            num_parts = (data_length + part_size - 1) // part_size
        part_size = (data_length + num_parts - 1) // num_parts
    elif qr_format == FORMAT_BBQR:
        data_length = len(data.payload)
        max_part_size = qr_capacity - BBQR_PREFIX_LENGTH
        if data_length < max_part_size:
            return 1, data_length
        max_part_size = (max_part_size // 8) * 8
        num_parts = (data_length + max_part_size - 1) // max_part_size
        part_size = data_length // num_parts
        part_size = ((part_size + 7) // 8) * 8
        if part_size > max_part_size:
            num_parts += 1
            part_size = data_length // num_parts
            part_size = ((part_size + 7) // 8) * 8
    else:
        raise ValueError("Invalid format type")
    return num_parts, part_size


def parse_pmofn_qr_part(data):
    of_index = data.index("of")
    space_index = data.index(" ")
    part_index = int(data[1:of_index])
    part_total = int(data[of_index + 2 : space_index])
    return data[space_index + 1 :], part_index, part_total


def detect_format(data):
    qr_format = FORMAT_NONE
    try:
        if data.startswith("p"):
            header = data.split(" ")[0]
            if "of" in header and header[1:].split("of")[0].isdigit():
                qr_format = FORMAT_PMOFN
        elif data.startswith("B$"):
            from .bbqr import BBQrCode, KNOWN_ENCODINGS, KNOWN_FILETYPES
            if data[3] in KNOWN_FILETYPES:
                bbqr_file_type = data[3]
                if data[2] in KNOWN_ENCODINGS:
                    bbqr_encoding = data[2]
                    return FORMAT_BBQR, BBQrCode(None, bbqr_encoding, bbqr_file_type)
    except:
        pass
    return qr_format, None
