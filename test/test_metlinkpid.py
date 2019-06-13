import dlestxetx
from pytest import raises

from metlinkpid import DisplayMessage, _crc, _uncrc, inspect, Page, PingMessage, ResponseMessage

FUNKYTOWN_STR = 'V40^12:34 FUNKYTOWN~5_Limited Express|H0^_Stops all stations except East Richard'


def test_page():
    page = Page.from_str('12:34 FUNKYTOWN~5_Limited Express')
    assert str(page) == 'N20^12:34 FUNKYTOWN~5_Limited Express'
    page = Page.from_bytes(b'\x00\x00\x00\x00\xFF')
    assert str(page) == 'N0^\N{REPLACEMENT CHARACTER}'

    with raises(ValueError):
        too_short = b'\x00\x00\x00'
        Page.from_bytes(too_short)
    with raises(NotImplementedError):
        Page.from_bytes(b'\xFF\x00\x00\x00')
    with raises(NotImplementedError):
        Page.from_bytes(b'\x00\x00\x00\xFF')
    with raises(ValueError):
        Page.from_str('@@@ BAD TEXT @@@').to_bytes()


def test_displaymessage():
    dm = DisplayMessage.from_str(FUNKYTOWN_STR)
    assert str(dm) == FUNKYTOWN_STR
    assert dm == eval(repr(dm))

    with raises(ValueError):
        DisplayMessage.from_bytes(b'')
    with raises(ValueError):
        DisplayMessage.from_bytes(b'\x01\x44\x00')
    with raises(ValueError):
        DisplayMessage.from_bytes(b'\x01\x44\x00\x00\x00\x00\x00\x0D\xFF')


def test_pingmessage():
    assert PingMessage.from_bytes(b'\x01\x50\x80').unspecified_byte == 0x80
    assert PingMessage.from_bytes(b'\x01\x50\x80').to_bytes() == b'\x01\x50\x80'

    with raises(ValueError):
        PingMessage.from_bytes(b'')
    with raises(ValueError):
        PingMessage.from_bytes(b'\x01\x50')
    with raises(ValueError):
        PingMessage.from_bytes(b'\x01\x50\x00\x00')


def test_responsemessage():
    assert ResponseMessage.from_bytes(b'\x01\x52\x80\x00').unspecified_byte == 0x80
    assert ResponseMessage.from_bytes(b'\x01\x52\x80\x00').to_bytes() == b'\x01\x52\x80\x00'

    with raises(ValueError):
        ResponseMessage.from_bytes(b'')
    with raises(ValueError):
        ResponseMessage.from_bytes(b'\x01\x52\x80')
    with raises(ValueError):
        ResponseMessage.from_bytes(b'\x01\x52\x80\x00\x00')
    with raises(ValueError):
        ResponseMessage.from_bytes(b'\x01\x52\x80\xFF')


def test_pid():
    # TODO: PID class tests need a suitable serial mocking interface.
    pass


def test_inspect():
    dm1 = DisplayMessage.from_str(FUNKYTOWN_STR)
    dm2 = inspect(dm1.to_bytes())
    assert dm1 == dm2

    framed = dlestxetx.encode(dm1.to_bytes() + _crc(dm1.to_bytes()))
    assert inspect(framed) == dm1

    with raises(ValueError):
        inspect(b'<bogus bytes>')


def test_crc():
    empty = bytes()
    with_crc = _crc(empty)
    without_crc = _uncrc(with_crc)
    assert empty == without_crc

    with raises(ValueError):
        too_short = b'\x00'
        _uncrc(too_short)
    with raises(ValueError):
        with_bad_crc = b'\x00\x00\x00'
        _uncrc(with_bad_crc)
