# -*- coding: utf-8 -*-

# PIV smartcard communication library for PIVageant
# Copyright (C) 2021-2022  BitLogiK
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>


import time
from hashlib import sha256, sha384
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

try:
    from smartcard.CardRequest import CardRequest
    from smartcard.util import toBytes, toHexString
    from smartcard.Exceptions import CardRequestTimeoutException
    from smartcard.pcsc.PCSCExceptions import EstablishContextException
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError("pyscard not installed or was not found") from exc
from lib.piv.compat_devices import COMPATIBLE_CARDS_ATR


# Exception classes for PIVcard


class PIVBaseException(Exception):
    pass


class PIVCardTimeoutException(PIVBaseException):
    pass


class PIVCardException(PIVBaseException):
    def __init__(self, sw_byte1, sw_byte2):
        self.sw_byte1 = sw_byte1
        self.sw_byte2 = sw_byte2
        self.sw_code = (sw_byte1 << 8) | sw_byte2
        self.message = "Error status : 0x%02X%02X" % (sw_byte1, sw_byte2)
        super().__init__(self.message)


class ConnectionException(PIVBaseException):
    pass


class BadInputException(PIVBaseException):
    pass


class DataException(PIVBaseException):
    pass


class PinException(PIVBaseException):
    def __init__(self, num_retries):
        self.retries_left = num_retries
        if num_retries >= 2:
            self.message = f"Wrong PIN. {num_retries} tries left"
        else:
            self.message = f"Wrong PIN. {num_retries} try left"
        super().__init__(self.message)


HEX_SYMBOLS = "0123456789abcdefABCDEF"


# Utils helpers


def ishex(istring):
    return all(c in HEX_SYMBOLS for c in istring)


def check_hex(func):
    """Decorator to check the first method argument"""
    #  is 2/4 string hex (a DO short address)
    # Expands the hex string from 2 to 4 hex chars (adds leading 0)
    def func_wrapper(*args):
        if len(args) < 2:
            BadInputException(
                "First argument must be filehex : 1 or 2 bytes hex string"
            )
        if not isinstance(args[1], str):
            BadInputException("filehex provided must be a string")
        args_list = [*args]
        if len(args_list[1]) == 2:
            # A single byte address : param_1=0
            args_list[1] = "00" + args_list[1]
        if len(args_list[1]) != 4 or not ishex(args_list[1]):
            raise BadInputException("filehex provided must be 2 or 4 hex chars")
        return func(*args_list)

    return func_wrapper


def to_list(binstr):
    return toBytes(binstr.hex())


def print_list(liststr):
    for item in liststr:
        print(f" - {item}")


def to_hex_list(liststr):
    ret = ""
    for item in liststr:
        ret += f" {item:02X}"
    return ret


def decode_hex_int(listint):
    """Read encoded number or date"""
    ret = ""
    for item in listint:
        ret += f"{item:02X}"
    return ret


def decode_dol(data, level=0):
    """Decode ASN1 BER/DER Data Objects into a Python object"""
    dol_out = {}
    idx = 0
    len_all_data = len(data)
    while idx < len_all_data:
        tag, idx, data_list = decode_do(data, idx)
        if (tag < 256 and tag & 32) or (tag >= 256 and tag & (32 << 8)):
            # constructed
            dol_out[f"{tag:02X}"] = decode_dol(data_list, level + 1)
        else:
            if dol_out.get(f"{tag:02X}"):
                if not isinstance(dol_out.get(f"{tag:02X}"), list):
                    dol_out[f"{tag:02X}"] = [dol_out[f"{tag:02X}"], bytes(data_list)]
                else:
                    dol_out[f"{tag:02X}"].append(bytes(data_list))
            else:
                dol_out[f"{tag:02X}"] = bytes(data_list)
    return dol_out


def decode_do(data, start_index):
    """Basic ASN1 BER/DER decoder for a DO"""
    i = start_index
    if data[i] & 31 == 31:
        # Tag has 2 bytes
        tag = data[i] * 256 + data[i + 1]
        i += 2
    else:
        # Tag is 1 byte
        tag = data[i]
        i += 1
    if data[i] & 128 > 0:
        # Composed len
        len_len = data[i] - 128
        len_data = 0
        while len_len:
            len_data *= 256
            i += 1
            len_data += data[i]
            len_len -= 1
        i += 1
    else:
        # Simple len
        len_data = data[i]
        i += 1
    data_read = data[i : i + len_data]
    return tag, i + len_data, data_read


def encode_do(do_data):
    """Add length header to data"""
    do_len = len(do_data)
    if do_len < 128:
        return [do_len, *do_data]
    if do_len < 256:
        return [0x81, do_len, *do_data]
    if do_len < 65536:
        return [0x82, do_len >> 8, do_len % 256, *do_data]
    raise BadInputException("Data too long.")


PIV_AID = "A0 00 00 03 08 00 00 10 00 01 00"


class CardsATRList:
    """A kind of CardType class to use a list of different possibles ATRs"""

    def __init__(self, atr_list):
        """Initialize the card type with a list of ATR"""
        self.atrs_list = atr_list

    def matches(self, atr, reader=None):
        return atr in self.atrs_list


# Algorithms constants
ALG_3DES = 0x03
ALG_RSA1024 = 0x06
ALG_RSA2048 = 0x07
ALG_AES128 = 0x08
ALG_AES192 = 0x0A
ALG_AES256 = 0x0C
ALG_ECP256 = 0x11
ALG_ECP384 = 0x14
ALG_CS2 = 0x27
ALG_CS7 = 0x27
# unofficials
ALG_ECP256_SHA1 = 0xF0
ALG_ECP256_SHA256 = 0xF1
ALG_ECP384_SHA1 = 0xF2
ALG_ECP384_SHA256 = 0xF3
ALG_ECP384_SHA384 = 0xF4


# Core class PIVcard


class PIVcard:

    AppID = toBytes(PIV_AID)
    compat_cards = [toBytes(atr) for atr in COMPATIBLE_CARDS_ATR]

    def __init__(self, connect_timeout, debug=False):
        self.debug = debug
        piv_card_atr = CardsATRList(PIVcard.compat_cards)
        try:
            cardrequest = CardRequest(timeout=connect_timeout, cardType=piv_card_atr)
            self.cardservice = cardrequest.waitforcard()
        except CardRequestTimeoutException:
            raise PIVCardTimeoutException
        except EstablishContextException as exc:
            if (
                str(exc) == "'Failure to establish context:"
                "The Smart Card Resource Manager is not running. '"
            ):
                raise ConnectionException("Can't start Scard service")
            raise exc
        self.cardservice.connection.connect()
        apdu_select = [
            0x00,
            0xA4,
            0x04,
            0x00,
            len(PIVcard.AppID),
        ] + PIVcard.AppID
        select_resp, sw_byte1, sw_byte2 = self.send_apdu(apdu_select)
        if sw_byte1 != 0x90 or sw_byte2 != 0x00:
            raise PIVCardException(sw_byte1, sw_byte2)
        card_info = decode_dol(select_resp)["61"]
        self.label = ""
        self.url_spec = ""
        self.algos = []
        self.hash_on_card = False
        self.sm_capable = False
        self.yubi_version = ""
        self.yubi_serial = 0
        self.is_yubico = False
        if card_info.get("50"):
            self.label = card_info["50"].decode("utf8")
        if card_info.get("AC"):
            self.algos = [ord(v) for v in card_info["AC"]["80"]]
        if self.algos and ((ALG_CS2 in self.algos) or (ALG_CS7 in self.algos)):
            self.sm_capable = True
        if ALG_ECP256_SHA256 in self.algos:
            self.hash_on_card = True
        self.yubi_version = self.yubi_get_version()
        self.is_yubico = bool(self.yubi_version)
        if self.is_yubico:
            self.yubi_serial = self.get_serial()
        if self.debug:
            print("PIV key connected :", self.label)
            if self.is_yubico:
                print(
                    " Yubico device version",
                    self.yubi_version,
                    "with serial =",
                    self.yubi_serial,
                )
            print(" Algorithms supported :", [f"0x{alg:02X}" for alg in self.algos])
            print(" Secure Messaging capable ?", "yes" if self.sm_capable else "no")
        time.sleep(0.25)

    def __del__(self):
        """Disconnect device"""
        if hasattr(self, "cardservice"):
            self.cardservice.connection.disconnect()
            del self.cardservice

    def send_apdu(self, apdu):
        """Send APDU. apdu is a list of integers (uint 8 array/list)"""
        # [ INS, CLA, param_1, param_2, Len, data... ]
        if self.debug:
            print(f" Sending 0x{apdu[1]:X} command with {(len(apdu) - 5)} bytes data")
            print(f"-> {toHexString(apdu)}")
            t_env = time.time()
        data, sw_byte1, sw_byte2 = self.cardservice.connection.transmit(apdu)
        if self.debug:
            t_ans = (time.time() - t_env) * 1000
            print(
                " Received %i bytes data : SW 0x%02X%02X - duration: %.1f ms"
                % (len(data), sw_byte1, sw_byte2, t_ans)
            )
            if len(data) > 0:
                print(f"<- {toHexString(data)}")
        return data, sw_byte1, sw_byte2

    def send_command(self, cmdh, data):
        """data can be int list or bytesarray"""
        i = 0
        lendata = len(data)
        if isinstance(data, list):
            full_data = bytes(data)
        else:  # bytes or bytearray
            full_data = data
        data_block_size = 247
        while lendata > data_block_size:
            data_apdu = full_data[i : i + data_block_size]
            apdu_command = cmdh + [len(data_apdu)] + to_list(data_apdu)
            apdu_command[0] |= 0x10
            self.send_apdu(apdu_command)
            i += data_block_size
            lendata -= data_block_size
        data_apdu = full_data[i:]
        apdu_command = cmdh + [len(data_apdu)] + to_list(data_apdu)
        datar, sw_byte1, sw_byte2 = self.send_apdu(apdu_command)
        while sw_byte1 == 0x61:
            if self.debug:
                t_env = time.time()
            datacompl, sw_byte1, sw_byte2 = self.cardservice.connection.transmit(
                [0x00, 0xC0, 0, 0, 0]
            )
            if self.debug:
                t_ans = int((time.time() - t_env) * 10000) / 10.0
                print(
                    " Received remaining %i bytes : 0x%02X%02X - duration: %.1f ms"
                    % (len(datacompl), sw_byte1, sw_byte2, t_ans)
                )
                print(f"<- {toHexString(datacompl)}")
            datar += datacompl
        if sw_byte1 == 0x63 and sw_byte2 & 0xF0 == 0xC0:
            raise PinException(sw_byte2 - 0xC0)
        if sw_byte1 != 0x90 or sw_byte2 != 0x00:
            raise PIVCardException(sw_byte1, sw_byte2)
        return datar

    def yubi_get_version(self):
        """Yubico extension"""
        version_command = [0x00, 0xFD, 0x00, 0x00]
        try:
            version_bin = self.send_command(version_command, b"")
            if len(version_bin) < 3:
                return ""
            return ".".join([str(c) for c in version_bin])
        except PIVCardException:
            return ""

    def get_serial(self):
        """Yubico extension, only available on Yubikey 5"""
        serial_command = [0x00, 0xF8, 0x00, 0x00]
        serial_bin = self.send_command(serial_command, b"")
        try:
            return int.from_bytes(serial_bin, "big")
        except PIVCardException:
            return 0

    def reset(self):
        """PIV extension, only available when both PIN and PUK are blocked."""
        reset_command = [0x00, 0xFB, 0x00, 0x00]
        return self.send_command(reset_command, b"")

    def general_authenticate(self, algo, keyref, data_auth):
        apdu_command = [
            0x00,
            0x87,
            algo,
            keyref,
        ]
        data = [0x7C, *encode_do(data_auth)]
        return self.send_command(apdu_command, data)

    def sign_ec(self, algo, keyref, message):
        """EC Sign a message"""
        if self.algos and algo not in self.algos:
            raise BadInputException("This PIV device doesn't support this algorithm")
        if self.hash_on_card:
            # PIV proprietary variant with hash on card
            hash_data = message
            algo = 0xF0 + (algo & 0x0F)
        else:
            # Fully compliant PIV device, device signs pre-hashed
            if algo == ALG_ECP256:
                hash_data = sha256(message).digest()
            elif algo == ALG_ECP384:
                hash_data = sha384(message).digest()
            else:
                raise BadInputException("EC sign shall be ECP256 0x11 or ECP384 0x14")
        # Response null, Challenge Hash/Data
        data = [0x82, 0x00, 0x81, *encode_do(hash_data)]
        return decode_dol(self.general_authenticate(algo, keyref, data))["7C"]["82"]

    def external_auth_admin(self, key_ref, keyalgo, auth_key):
        # keyalgo : See NIST 800-78-4 6.2 & 6.3
        # auth_type = 0x81 # challenge - See PIV NIST 800-73-4 3.2.4 Table 7
        chall_resp = self.general_authenticate(keyalgo, key_ref, [0x81, 0])
        if chall_resp[:4] != [0x7C, 0x0A, 0x81, 8] or len(chall_resp) != 12:
            raise DataException("Bad data received from External Authenticate command")
        challenge = bytes(chall_resp[4:])
        # Encrypt challenge (with keyalgo 00/03 TDES)
        enc_algo = algorithms.TripleDES(auth_key)
        mode_algo = modes.ECB()
        cipher = Cipher(enc_algo, mode_algo)
        encryptor = cipher.encryptor()
        data_enc = encryptor.update(challenge)
        # Response 0x82
        resp_data = [0x82, *encode_do(data_enc)]
        # 0x6982 status if rejected
        auth_resp = self.general_authenticate(keyalgo, key_ref, resp_data)
        return auth_resp

    def gen_asymmetric(self, keyref, keyalgo):
        """Generate a key pair"""
        # key algo : PIV NIST 800-73-4 Part 1 5.3 Table 5
        apdu_command = [
            0x00,
            0x47,
            0,
            keyref,
        ]
        data = [0xAC, 3, 0x80, 1, keyalgo]
        if self.is_yubico:
            # Add extention for touch confirmation
            data[1] = 6
            data.extend([0xAB, 1, 0x02])
        gen_resp = self.send_command(apdu_command, data)
        if gen_resp[:2] != [0x7F, 0x49] or len(gen_resp) != gen_resp[2] + 3:
            raise DataException("Bad data received from Generate Asymmetric command")
        # if ECC (11 ou  14) -> gen_resp[2] == 0x86
        # if ECC384, keyalg = 0x14 -> gen_resp[4]:keylen == 97
        # return public key data, for ECC 86 : 04 ..
        return decode_dol(gen_resp[3:])

    def get_data(self, file_tlv_hex):
        """Binary read / ISO read the object"""
        lenaddr = len(file_tlv_hex) // 2
        data_hex = f"5C{lenaddr:02X}{file_tlv_hex}"
        if self.debug:
            print(f"Read Data in 0x{file_tlv_hex}")
        apdu_command = [0x00, 0xCB, 0x3F, 0xFF]
        data = bytes.fromhex(data_hex)
        dataresp = self.send_command(apdu_command, data)
        if lenaddr == 3:
            if dataresp[0] != 0x53:
                raise DataException("Bad data received from Get Data command")
            return decode_dol(dataresp)["53"]
        if lenaddr == 1 and dataresp[0] != int(file_tlv_hex, 16):
            raise DataException("Bad data received from Get Data command")
        return decode_dol(dataresp)[file_tlv_hex]

    def put_data(self, file_tlv_hex, data_bin):
        """Binary write / ISO write the object"""
        data_hex = "5C03" + file_tlv_hex
        if self.debug:
            print(f"Put Data {data_bin.hex()} in 0x{file_tlv_hex}")
        len_data_bin_b1 = len(data_bin) >> 8
        len_data_bin_b2 = len(data_bin) % 256
        full_data = (
            bytes.fromhex(data_hex)
            + bytes([0x53, 0x82, len_data_bin_b1, len_data_bin_b2])
            + data_bin
        )
        apdu_command = [0x00, 0xDB, 0x3F, 0xFF]
        self.send_command(apdu_command, full_data)

    def get_pin_status(self, pin_bank):
        """Return remaining tries left for the given PIN bank address"""
        # if 0 : PIN is blocked, if 9000 : PIN has been verified
        try:
            self.verify_pin(pin_bank, "")
            return 9000
        except PinException as exc:
            return exc.retries_left
        except PIVCardException as exc:
            if exc.sw_code == 0x6983:
                return 0
            raise

    def verify_pin(self, pin_bank, pin_string):
        """Verify PIN code : pin_bank"""
        if pin_string:
            pin_data = pin_string.encode("ascii")
            while len(pin_data) < 8:
                pin_data += b"\xFF"
            self.send_command([0, 0x20, 0, pin_bank], pin_data)
        else:
            self.send_command([0, 0x20, 0, pin_bank], b"")
