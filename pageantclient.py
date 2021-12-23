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


from cryptography import x509
from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding
from ssh_encodings import (
    encode_openssh,
    pack_reply,
    read_len,
    parse_sign_command,
    parse_datasig,
    decode_sig,
)
from piv_card import PIVcard, ALG_ECP256, ALG_ECP384

OP_REQUEST_IDS = 11
IDS_RESPONSE = 12
OP_SIGN_REQUEST = 13
SIGN_RESPONSE = 14
ERROR_CODE = b"\x05"


def read_pubkey(keyname, timeout):
    # Read the PIV key certificate
    # X509 decoding, then encoded to OpenSSH format
    my_piv_card = PIVcard(timeout, True)
    cert_raw = my_piv_card.get_data("5FC101")
    cert = x509.load_der_x509_certificate(cert_raw[4:-5])
    pubkey = cert.public_key().public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )
    return encode_openssh(pubkey, keyname)


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


def list_identitites(ssh_wire_key):
    # Raw list of keys
    # return b"\x0c\x00\x00\x00\x01" + openssh_to_wire()
    list_type = IDS_RESPONSE.to_bytes(1, byteorder="big")
    n_ids_int = 1
    nkeys = n_ids_int.to_bytes(4, byteorder="big")
    return list_type + nkeys + ssh_wire_key


def sign_request(sign_req, local_ssh_key, open_user_modal, debug_piv=False):
    """Parse, check and sign the signature query"""
    key_type = local_ssh_key[24:27]
    if key_type == b"256":
        keyalgo = ALG_ECP256
    elif key_type == b"384":
        keyalgo = ALG_ECP384
    else:
        raise Exception("Incompatible key type")
    SIG_HEADER_STRING = b"ecdsa-sha2-nistp" + key_type
    signature_data = parse_sign_command(sign_req, debug_piv)
    print("Data to sign request :", signature_data)
    current_card = PIVcard(15, debug_piv)
    if debug_piv:
        print("PIV device detected")
    # Check data to be signed
    sig_data = parse_datasig(signature_data)
    local_pubkey = pack_reply(local_ssh_key[4 : 4 + read_len(local_ssh_key)])
    sig_header = pack_reply(SIG_HEADER_STRING)
    # Sign query is for the same public key ?
    if sig_data["publickey"] != sig_header + local_pubkey:
        raise Exception("Public key mismatch")
    # All checks OK, proceed to sign
    open_user_modal(sig_data["username"])
    key_slot_gen = 0x9E
    der_signature = current_card.sign_ec(keyalgo, key_slot_gen, signature_data)
    del current_card
    sig_type = SIGN_RESPONSE.to_bytes(1, byteorder="big")
    signature = pack_reply(decode_sig(der_signature))
    return sig_type + pack_reply(sig_header + signature)
