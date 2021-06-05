import datetime


def get_win32_filetime():
    diff = datetime.datetime.now() - datetime.datetime(1601, 1, 1)
    return int((diff / datetime.timedelta(microseconds=1)) * 10)


def int_to_32bpair(integ):
    return (integ >> 32, integ & 0xFFFFFFFF)


def now_time_filetime():
    return int_to_32bpair(get_win32_filetime())


def ver_str_to_comma(verstr):
    return ", ".join(verstr.split("."))


def fill_version_info(file_name, version_str, file_desc, comment):
    with open("package/version_info_form", "r", encoding="utf-8") as fverinfoform:
        versioninfo_content = fverinfoform.read()
    ver_commas = ver_str_to_comma(version_str)
    year = datetime.datetime.today().year
    versioninfo_new = versioninfo_content.format(
        version_str,
        ver_commas,
        year,
        file_desc,
        comment,
        now_time_filetime(),
        file_name,
    )
    print(versioninfo_new)
    with open("package/version_info", "w", encoding="utf-8") as fverinfo:
        fverinfo.write(versioninfo_new)
