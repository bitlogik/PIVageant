
# PIVageant

Pageant compatible SSH agent for Windows

using a PIV dongle.

![PIVageant logo](windesign/pivpagent-logo.png)

Compatible with :
* all [Yubico 5 series](https://www.yubico.com/products/yubikey-5-overview/) : YubiKey 5 NFC, YubiKey 5C NFC, YubiKey 5Ci, YubiKey 5 Nano, YubiKey 5C, YubiKey 5C Nano, YubiKey 5 NFC FIPS, YubiKey 5C NFC FIPS, YubiKey 5Ci FIPS, YubiKey 5 Nano FIPS, YubiKey 5C FIPS and YubiKey 5C Nano FIPS
* Yubico Yubikey Neo
* Yubico Yubikey 4 series
* Feitian [ePass Plus PIV](https://shop.ftsafe.us/collections/fido2/piv)

Potentially with any PIV card or USB dongle.  
What is needed is to list the dongle/card ATR in COMPATIBLE_CARDS_HEX in lib/piv/piv_card.

## Use

### Download

Get the Windows binary exe [distributed in Github releases](https://github.com/bitlogik/PIVageant/releases/latest).

To increase the security, the Windows exe released is signed with our [Extended
Validation certificate](https://en.wikipedia.org/wiki/Code_signing#Extended_validation_(EV)_code_signing),
bringing even greater confidence in the integrity of the software.

### Use the agent

Start the agent :

Run *PIVageant.exe*

or `python3w PIVageant.pyw` from source

After detecting your PIV dongle, it hides automatically to tray if it can read a public key. Then it monitors the Pageant queries (from Putty or compatible SSH Windows clients) and redirects the signature to the PIV key.

When minimized, it goes to the tray icons bar. Any click on the icon restore the window.

### Generate a key in a YubiKey

Click on the "+ new key" button in PIVageant, then confirm.
It will generate an ECDSA key (256 or 384 bits if possible) using some standards administrator default keys.

The key certificate written in the PIV dongle is not even self-signed, but with a fake invalid signature. It only holds the public key, to read the EC public key.

## Development

To run from source :

`python3 setup.py install`

or install :

* Python3 >= 3.6
* wxPython 4.1.1
* pyscard 2.0.1
* cryptography 36.0.1

To build the binaries, you need Python 3.9 and Pyinstaller. Start the Build-Windows.bat script in the *package* directory. Output result in the *dist* directory.

PIVageant can be run with the "-v" options to display various debug informations.

`python3 PIVageant.pyw -v`
