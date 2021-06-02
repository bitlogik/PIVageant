
# PIVageant

Pageant compatible SSH agent for Windows

using Yubico YubiKey 5 security dongles, PIV application

![PIVageant logo](windesign/pivpagent-logo.png)

Compatible with all Yubico 5 series : YubiKey 5 NFC, YubiKey 5C NFC, YubiKey 5Ci, YubiKey 5 Nano, YubiKey 5C, YubiKey 5C Nano, YubiKey 5 NFC FIPS, YubiKey 5C NFC FIPS, YubiKey 5Ci FIPS, YubiKey 5 Nano FIPS, YubiKey 5C FIPS and YubiKey 5C Nano FIPS.


## Use

### Download

Get the Windows binary exe ZIP package [distributed in Github releases](https://github.com/bitlogik/PIVageant/releases/latest).

To increase the security, the Windows exe released are signed with our [Extended
Validation certificate](https://en.wikipedia.org/wiki/Code_signing#Extended_validation_(EV)_code_signing),
bringing even greater confidence in the integrity of the software.

Unzip anywhere, there are 2 exe files. One for setup and generate the key in a YubiKey. The other is the SSH agent.

### Generate a key in a YubiKey

Run *Gen-keys.exe*

or `python3 Gen-keys.py` from source

### Use the agent

Start the agent :

Run *PIVageant.exe*

or `python3w PIVageant.pyw` from source

It monitors the Pageant queries (from Putty or compatible SSH Windows clients) and redirects the signature to a Yubico 5 PIV key.

## Development

To run from source :

* Python3 >= 3.6
* wxPython 4.1.1
* pyscard 2.0.0
* cryptography 3.4.6

To build the binaries, you need Python 3.8 and Pyinstaller. Start the Build-Windows.bat script in the *package* directory. Output result in the *dist* directory.
