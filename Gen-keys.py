#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Generate 9E key EC384 with touch
# To use Yubico 5 with PIVageant
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
import subprocess
from _version import __version__
import piv_card

ADMIN_KEY = "010203040506070801020304050607080102030405060708"
KEY_NAME = "yub384"


def build_certificate(datakey):
    # fake signature
    return (
        "7082015b308201573081dfa003020102021465fb4509c1e90575ef9eccc57f5f"
        "96ffc56b22b7300a06082a8648ce3d040302300e310c300a06035504030c0353"
        "5348301e170d3231303232373133333532395a170d3332303232353030303030"
        "305a300e310c300a06035504030c035353483076301006072a8648ce3d020106"
        "052b81040022036200"
        + datakey.hex()
        + "300a06082a8648ce3d040302036700306402300331a54b279f7f91e41f81b814"
        "dfec2190e24155824f402ca333f1a9bbc8b985f91bb12a7b7432faae142943db"
        "2a4fcb0230704fd3f7a8f6101c5e2dcee92b2eeca398550a482618f6024a8a71"
        "079fa0ddae4e53aee330b62201a651e04b1d73d418710100fe00"
    )


def encode_openssh(pubkey_bytes, comment_text):  # for ECP384
    if len(pubkey_bytes) != 97:
        raise Exception("invalid public key length")
    # "ecdsa-sha2-nistp384", "nistp384", header len pubkey
    header_hex = (
        "0000001365636473612D736861322D6E69737470333834000000086E69737470"
        "33383400000061"
    )
    pubkey_b64 = base64.b64encode(bytes.fromhex(header_hex) + pubkey_bytes).decode(
        "ascii"
    )
    return f"ecdsa-sha2-nistp384 {pubkey_b64} {comment_text}"


def decode_ssh(data):
    ssh_data = data.split(" ")[1]
    return base64.b64decode(ssh_data)


fake_or_PKI = "fake"


def main():
    print("\n PIVageant Gen-keys version ", __version__)
    print("Waiting for a Yubico 5 ...")
    print(" press CTRL+C to cancel")
    current_card = None
    while not current_card:
        try:
            current_card = piv_card.PIVcard(1)
        except KeyboardInterrupt:
            return
        except piv_card.PIVCardTimeoutException:
            continue
    print("OK, Yubico 5 with PIV detected")
    admin_keyref = 0x9B
    algo_used = 0x03
    # get pass
    admin_key = bytes.fromhex(ADMIN_KEY)
    current_card.external_auth_admin(admin_keyref, algo_used, admin_key)
    key_slot_gen = 0x9E  # Card auth key
    keyalgo = 0x14  # ECC 384
    Data_slot_ID = "5FC101"
    # key_slot_gen = 0x9C # Digital Signature Key
    # keyalgo = 0x14 # ECC 384
    # Data_slot_ID = "5FC10A"
    pubkey_resp = current_card.gen_asymmetric(key_slot_gen, keyalgo)
    openssh_pukey = encode_openssh(pubkey_resp["86"], KEY_NAME)
    print("\nCard authentication key generated with ECP384 :\n")
    print(openssh_pukey)
    print("")
    key_parts = openssh_pukey.split(" ")
    print("---- BEGIN SSH2 PUBLIC KEY ----")
    print(f'Comment: "{key_parts[2]}"')
    print(key_parts[1])
    print("---- END SSH2 PUBLIC KEY ----")
    print("")
    pubkey_bin = pubkey_resp["86"]
    # Generate certificate for this key
    if fake_or_PKI == "fake":
        cert_data_hex = build_certificate(pubkey_bin)
    else:
        f = open("pivkey.pub", "w")
        f.write(openssh_pukey)
        f.close()
        sign_cmd = "ssh-keygen -s ssh-ca -I piv pivkey.pub"
        subprocess.run(sign_cmd, shell=True, check=True, stdout=subprocess.PIPE)
    # Write certificate in the card
    if fake_or_PKI == "fake":
        current_card.put_data(Data_slot_ID, bytes.fromhex(cert_data_hex))
    else:
        fr = open("pivkey-cert.pub", "r")
        fr.seek(0)
        cert_data = fr.read()
        fr.close()
        current_card.put_data(Data_slot_ID, decode_ssh(cert_data))
    # Read cert 0x0500 to confirm
    read_cert = current_card.get_data(Data_slot_ID).hex()
    assert read_cert == cert_data_hex
    print("PIV card programmed successfully.")
    input("Press RETURN to quit")


if __name__ == "__main__":
    main()
