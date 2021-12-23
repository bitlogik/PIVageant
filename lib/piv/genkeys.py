#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Generate 9E key ECDSA with touch when possible
# To use a PIV dongle with PIVageant
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


import subprocess
from lib.piv.piv_card import (
    PIVcard,
    PIVCardException,
    ALG_ECP256,
    ALG_ECP384,
)
from lib.ssh.ssh_encodings import decode_ssh, encode_openssh


ADMIN_KEYS = [
    "010203040506070801020304050607080102030405060708",
    "313233343536373831323334353637383132333435363738",
]
KEY_NAME = "ECPSSHKey"


def build_certificate(datakey, key_algo):
    """Build a certificate with a fake signature"""
    if key_algo != ALG_ECP256 and key_algo != ALG_ECP384:
        raise Exception("Incompatible key algo")
    if key_algo == ALG_ECP256 and len(datakey) != 65:
        raise Exception("invalid public key length")
    if key_algo == ALG_ECP384 and len(datakey) != 97:
        raise Exception("invalid public key length")
    cert_hex = "7082"
    if key_algo == ALG_ECP384:
        cert_hex += "015b"
    else:
        cert_hex += "013e"
    cert_hex += "3082"
    if key_algo == ALG_ECP384:
        cert_hex += "01573081df"
    else:
        cert_hex += "013a3081c2"
    cert_hex += (
        "a003020102021465fb4509c1e90575ef9eccc57f5f"
        "96ffc56b22b7300a06082a8648ce3d040302300e310c300a06035504030c0353"
        "5348301e170d3231303232373133333532395a170d3332303232353030303030"
        "305a300e310c300a06035504030c03535348"
        "30"
    )
    if key_algo == ALG_ECP384:
        cert_hex += "763010"
    else:
        cert_hex += "593013"
    cert_hex += "06072a8648ce3d0201"
    if key_algo == ALG_ECP384:
        # OID : 1.3.132.0.34
        cert_hex += "06052b81040022036200"
    else:
        # OID : 1.2.840.10045.3.1.7
        cert_hex += "06082a8648ce3d030107034200"
    cert_hex += datakey.hex()
    cert_hex += (
        "300a06082a8648ce3d040302036700306402300331a54b279f7f91e41f81b814"
        "dfec2190e24155824f402ca333f1a9bbc8b985f91bb12a7b7432faae142943db"
        "2a4fcb0230704fd3f7a8f6101c5e2dcee92b2eeca398550a482618f6024a8a71"
        "079fa0ddae4e53aee330b62201a651e04b1d73d418710100fe00"
    )
    return bytes.fromhex(cert_hex)


fake_or_PKI = "fake"


def generate_key(debug=False):
    current_card = PIVcard(0.2)
    admin_keyref = 0x9B
    algo_used = 0x03
    # Auth admin
    for admin_key in ADMIN_KEYS:
        admin_key = bytes.fromhex(admin_key)
        try:
            current_card.external_auth_admin(admin_keyref, algo_used, admin_key)
        except PIVCardException:
            continue
        break
    key_slot_gen = 0x9E  # Card auth key
    Data_slot_ID = "5FC101"
    # key_slot_gen = 0x9C # Digital Signature Key
    # Data_slot_ID = "5FC10A"
    keyalgo = 0x14  # EC 384
    try:
        # try with EC 384 bits
        pubkey_resp = current_card.gen_asymmetric(key_slot_gen, keyalgo)
    except PIVCardException:
        keyalgo = 0x11  # Fallback to EC 256
        pubkey_resp = current_card.gen_asymmetric(key_slot_gen, keyalgo)
    openssh_pukey = encode_openssh(pubkey_resp["86"], KEY_NAME)
    if debug:
        print("\nCard authentication key generated with EC :\n")
        print(openssh_pukey)
        key_parts = openssh_pukey.split(" ")
        print("---- BEGIN SSH2 PUBLIC KEY ----")
        print(f'Comment: "{key_parts[2]}"')
        print(key_parts[1])
        print("---- END SSH2 PUBLIC KEY ----")
        print("")
    pubkey_bin = pubkey_resp["86"]
    # Generate certificate for this key
    if fake_or_PKI == "fake":
        cert_data = build_certificate(pubkey_bin, keyalgo)
    else:
        f = open("pivkey.pub", "w")
        f.write(openssh_pukey)
        f.close()
        sign_cmd = "ssh-keygen -s ssh-ca -I piv pivkey.pub"
        subprocess.run(sign_cmd, shell=True, check=True, stdout=subprocess.PIPE)
    # Write certificate in the card
    if fake_or_PKI == "fake":
        current_card.put_data(Data_slot_ID, cert_data)
    else:
        fr = open("pivkey-cert.pub", "r")
        fr.seek(0)
        cert_data = fr.read()
        fr.close()
        current_card.put_data(Data_slot_ID, decode_ssh(cert_data))
    # Read cert 0x0500 to confirm
    read_cert = current_card.get_data(Data_slot_ID)
    assert read_cert == cert_data
    if debug:
        print("PIV card EC key generated successfully.")
    return
