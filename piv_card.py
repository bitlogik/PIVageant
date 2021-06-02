#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PIV smartcard communication library for PIVageant
# Copyright (C) 2021  BitLogiK
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

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

try:
    from smartcard.CardType import ATRCardType
    from smartcard.CardRequest import CardRequest
    from smartcard.util import toBytes, toHexString
    from smartcard.Exceptions import CardRequestTimeoutException
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError("pyscard not installed or was not found") from exc


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
    # Decorator to check the first method argument
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
    # read encoded number or date
    ret = ""
    for item in listint:
        ret += f"{item:02X}"
    return ret


def decode_dol(data, level=0):
    # Decode ASN1 BER/DER Data Objects into a Python object
    dol_out = {}
    idx = 0
    len_all_data = len(data)
    while idx < len_all_data:
        tag, idx, data_list = decode_do(data, idx)
        if (tag < 256 and tag & 32) or (tag >= 256 and tag & (32 << 8)):
            # constructed
            dol_out[f"{tag:02X}"] = decode_dol(data_list, level + 1)
        else:
            dol_out[f"{tag:02X}"] = bytes(data_list)
    return dol_out


def decode_do(data, start_index):
    # Basic ASN1 BER/DER decoder for a DO
    i = start_index
    if data[i] & 31 == 31:
        # Tag has 2 bytes
        tag = data[i] * 256 + data[i + 1]
        i += 2
    else:
        # tag is 1 byte
        tag = data[i]
        i += 1
    if data[i] & 128 > 0:
        # composed len
        len_len = data[i] - 128
        len_data = 0
        while len_len:
            len_data *= 256
            i += 1
            len_data += data[i]  # struct.unpack("B"*len_len, data[i+1:i+1+len_len])
            len_len -= 1
        i += 1
    else:
        # simple len
        len_data = data[i]
        i += 1
    data_read = data[i : i + len_data]
    return tag, i + len_data, data_read


# Core class PIVcard


class PIVcard:

    AppID = toBytes("A000000308000010000100")
    YUBICO5_ATR_HEX = toBytes("3BFD1300008131FE158073C021C057597562694B657940")

    def __init__(self, connect_timeout, debug=False):
        self.debug = debug
        piv_card_atr = ATRCardType(PIVcard.YUBICO5_ATR_HEX)
        cardrequest = CardRequest(timeout=connect_timeout, cardType=piv_card_atr)
        try:
            self.cardservice = cardrequest.waitforcard()
        except CardRequestTimeoutException:
            raise PIVCardTimeoutException
        self.cardservice.connection.connect()
        apdu_select = [
            0x00,
            0xA4,
            0x04,
            0x00,
            len(PIVcard.AppID),
        ] + PIVcard.AppID
        self.send_apdu(apdu_select)
        time.sleep(0.25)

    def __del__(self):
        # Disconnect device
        if hasattr(self, "cardservice"):
            self.cardservice.connection.disconnect()
            del self.cardservice

    def send_apdu(self, apdu):
        # send APDU. apdu is a list of integers (uint 8 array/list)
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
        # data can be int list or bytesarray
        i = 0
        lendata = len(data)
        if isinstance(data, list):
            full_data = bytes(data)
        else:  # bytes or bytearray
            full_data = data
        DATA_BLOCK_SIZE = 247
        while lendata > DATA_BLOCK_SIZE:
            data_apdu = full_data[i : i + DATA_BLOCK_SIZE]
            apdu_command = cmdh + [len(data_apdu)] + to_list(data_apdu)
            apdu_command[0] |= 0x10
            self.send_apdu(apdu_command)
            i += DATA_BLOCK_SIZE
            lendata -= DATA_BLOCK_SIZE
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

    def general_authenticate(self, algo, keyref, data_auth):
        apdu_command = [
            0x00,
            0x87,
            algo,
            keyref,
        ]
        data = [0x7C, len(data_auth), *data_auth]
        return self.send_command(apdu_command, data)

    def sign_ec(self, algo, keyref, hash_data):
        data = [0x82, 0x00, 0x81, len(hash_data), *hash_data]
        return decode_dol(self.general_authenticate(algo, keyref, data))["7C"]["82"]

    def external_auth_admin(self, key_ref, keyalgo, auth_key):
        # keyalgo : See NIST 800-78-4 6.2 & 6.3
        # auth_type = 0x81 # challenge - See PIV NIST 800-73-4 3.2.4 Table 7
        chall_resp = self.general_authenticate(keyalgo, key_ref, [0x81, 0])
        if chall_resp[:4] != [0x7C, 0x0A, 0x81, 8] or len(chall_resp) != 12:
            raise DataException("Bad data received from External Authenticate command")
        challenge = bytes(chall_resp[4:])
        # Encrypt challenge (with keyalgo 00/00 TDES)
        enc_algo = algorithms.TripleDES(auth_key)
        mode_algo = modes.ECB()
        cipher = Cipher(enc_algo, mode_algo)
        encryptor = cipher.encryptor()
        ct = encryptor.update(challenge)
        # Response 0x82
        resp_data = [0x82, len(ct)] + to_list(ct)
        # 0x6982 status if rejected
        auth_resp = self.general_authenticate(keyalgo, key_ref, resp_data)
        return auth_resp

    def gen_asymmetric(self, keyref, keyalgo):
        # 0 0x47 0 0x9E L 0xAC 3 0x80 1 ALGO 0xAB 1 2
        # key algo : PIV NIST 800-73-4 Part 1 5.3 Table 5
        apdu_command = [
            0x00,
            0x47,
            0,
            keyref,
        ]
        data = [
            0xAC,
            6,
            0x80,
            1,
            keyalgo,
            0xAB,
            1,
            0x02,
        ]
        gen_resp = self.send_command(apdu_command, data)
        if gen_resp[:2] != [0x7F, 0x49] or len(gen_resp) != gen_resp[2] + 3:
            raise DataException("Bad data received from Generate Asymmetric command")
        # if ECC (11 ou  14) -> gen_resp[2] == 0x86
        # if ECC384, keyalg = 0x14 -> gen_resp[4]:keylen == 97
        # return public key data, for ECC 86 : 04 ..
        return decode_dol(gen_resp[3:])
        # ToDo ? : build certificate for this key
        # Upload it in container id 0x0500 TLV: '5FC101'
        # For now, done by agent files

    def get_data(self, fileTLVhex):
        # Binary read / ISO read the object
        lenaddr = len(fileTLVhex) // 2
        data_hex = f"5C{'%02X'%lenaddr}" + fileTLVhex
        if self.debug:
            print(f"Read Data {data_hex} in 0x{fileTLVhex}")
        apdu_command = [0x00, 0xCB, 0x3F, 0xFF]
        data = bytes.fromhex(data_hex)
        dataresp = self.send_command(apdu_command, data)
        if lenaddr == 3:
            if dataresp[0] != 0x53:
                raise DataException("Bad data received from Get Data command")
            return decode_dol(dataresp)["53"]
        if lenaddr == 1 and dataresp[0] != int(fileTLVhex, 16):
            raise DataException("Bad data received from Get Data command")
        return decode_dol(dataresp)[fileTLVhex]

    def put_data(self, fileTLVhex, data_bin):
        # Binary read / ISO read the object
        data_hex = "5C03" + fileTLVhex
        if self.debug:
            print(f"Put Data {data_bin.hex()} in 0x{fileTLVhex}")
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
        # return remaining tries left for the given PIN bank address
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
        # Verify PIN code : pin_bank
        if pin_string:
            self.send_command([0, 0x20, 0, pin_bank], pin_string.encode("ascii"))
        else:
            self.send_command([0, 0x20, 0, pin_bank])
