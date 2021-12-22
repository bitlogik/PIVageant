#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pageant SSH agent client methods for PIVageant
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

import base64

from cryptography import x509
from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding
import piv_card

OP_REQUEST_IDS = 11
IDS_RESPONSE = 12
OP_SIGN_REQUEST = 13
SIGN_RESPONSE = 14
ERROR_CODE = b"\x05"


def pack_reply(reply_msg):
    # Add message length header, as per SSH and agent protocol
    uintlen = (len(reply_msg)).to_bytes(4, byteorder="big")
    return uintlen + reply_msg


def read_len(buffer):
    # Return the message length header as integer
    return int.from_bytes(buffer[:4], "big")


def encode_pubkey(pubkey, identifier, key_blob_id):
    return (
        pack_reply(identifier.encode("ascii"))
        + pack_reply(key_blob_id.encode("ascii"))
        + pack_reply(pubkey)
    )


def parse_datasig(data):
    # Parse and validate the data to be signed
    # According to RFC4252 7.
    i = 0
    len_part = read_len(data[i:])
    i += 4
    session_id = data[i : i + len_part]
    i += len_part
    assert data[i] == 50  # SSH_MSG_USERAUTH_REQUEST
    i += 1
    len_part = read_len(data[i:])
    i += 4
    username = data[i : i + len_part].decode("utf8")
    i += len_part
    len_part = read_len(data[i:])
    i += 4
    # Service name
    assert data[i : i + len_part] == b"ssh-connection"
    i += len_part
    len_part = read_len(data[i:])
    i += 4
    # Authentication Method Name
    assert data[i : i + len_part] == b"publickey"
    i += len_part
    assert data[i] == 1  # True
    i += 1
    publickey = data[i:]
    return {"session_id": session_id, "username": username, "publickey": publickey}


def read_pubkey(keyname, timeout):
    # Read the PIV key certificate
    # X509 decoding, then encoded to OpenSSH format
    my_piv_card = piv_card.PIVcard(timeout, True)
    cert_raw = my_piv_card.get_data("5FC101")
    cert = x509.load_der_x509_certificate(cert_raw[4:-5])
    pubkey = cert.public_key().public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )
    # For EC key
    curve_id = "nistp256"
    if len(pubkey) == 97:
        curve_id = "nistp384"
    key_id = f"ecdsa-sha2-{curve_id}"
    pubkey_encoded = encode_pubkey(pubkey, key_id, curve_id)
    return f"{key_id} {base64.b64encode(pubkey_encoded).decode('ascii')} {keyname}"


def decode_sig(sig):
    # DER to packed mpint blob R|S - RFC5656 3.1.2
    if sig[0] != 0x30:
        raise Exception("Wrong signature header")
    if sig[2] != 0x02:
        raise Exception("Wrong signature format")
    rlen = sig[3]
    slen = sig[5 + rlen]
    r_bytes = sig[4 : 4 + rlen]
    s_bytes = sig[6 + rlen : 6 + rlen + slen]
    return pack_reply(r_bytes) + pack_reply(s_bytes)


def process_command(debug_agent, ssh_wire_key, show_main_win, finish_cb, data=b""):
    # Entry point to this Pageant client
    request_type = data[0]
    request_data = data[1:]
    if debug_agent:
        print("Command received")
        print("Request type :", request_type)
        print(" data :", request_data)
    reply = ERROR_CODE
    try:
        if request_type == OP_REQUEST_IDS:
            reply = list_identitites(ssh_wire_key)
        if request_type == OP_SIGN_REQUEST:
            # sign request
            reply = sign_request(request_data, ssh_wire_key, show_main_win, debug_agent)
            finish_cb("Signed OK")
    except Exception as exc:
        if debug_agent:
            print("Error when processing command :")
            print(exc)
        if request_type == OP_SIGN_REQUEST and str(exc) == "Error status : 0x6982":
            finish_cb("Not approved in time")
    finally:
        return pack_reply(reply)


def openssh_to_wire(key_openssh):
    # Serialize an RFC4253 OpenSSH public key from text to binary
    key_data = key_openssh.split(" ")
    return pack_reply(base64.b64decode(key_data[1])) + pack_reply(
        bytes(key_data[2], "utf8")
    )


def list_identitites(ssh_wire_key):
    # Raw list of keys
    # return b"\x0c\x00\x00\x00\x01" + openssh_to_wire()
    list_type = IDS_RESPONSE.to_bytes(1, byteorder="big")
    n_ids_int = 1
    nkeys = n_ids_int.to_bytes(4, byteorder="big")
    return list_type + nkeys + ssh_wire_key


def parse_sign_command(sign_cmd, debug):
    # Parse sign query, and extract the data to sign
    idseek = 0
    keyblob_len = read_len(sign_cmd)
    idseek += 4
    key_blob = sign_cmd[idseek : idseek + keyblob_len]
    idseek += keyblob_len
    data_len = read_len(sign_cmd[idseek:])
    idseek += 4
    data_tosign = sign_cmd[idseek : idseek + data_len]
    idseek += data_len
    if debug:
        print("Key blob for signature :", key_blob)
        print("Data to sign :", data_tosign)
    if sign_cmd[idseek:] != b"\0\0\0\0":
        raise Exception("Unvalid signature query, must be compliant for ECC.")
    return data_tosign


def sign_request(sign_req, local_ssh_key, open_user_modal, debug_piv=False):
    # Parse, check and sign the signature query
    SIG_HEADER_STRING = b"ecdsa-sha2-nistp256"
    signature_data = parse_sign_command(sign_req, debug_piv)
    print("Data to sign request :", signature_data)
    current_card = piv_card.PIVcard(15, debug_piv)
    if debug_piv:
        print("PIV device detected")
    # Check data to be signed
    sig_data = parse_datasig(signature_data)
    local_pubkey = pack_reply(local_ssh_key[4 : 4 + read_len(local_ssh_key)])
    # Sign query is for the same public key ?
    assert sig_data["publickey"] == pack_reply(SIG_HEADER_STRING) + local_pubkey
    # All checks OK, proceed to sign
    open_user_modal(sig_data["username"])
    key_slot_gen = 0x9E
    keyalgo = 0x11  # ECC 384
    der_signature = current_card.sign_ec(keyalgo, key_slot_gen, signature_data)
    del current_card
    sig_type = SIGN_RESPONSE.to_bytes(1, byteorder="big")
    sig_header = pack_reply(SIG_HEADER_STRING)
    signature = pack_reply(decode_sig(der_signature))
    return sig_type + pack_reply(sig_header + signature)
