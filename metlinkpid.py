import re
import struct
from abc import ABC, abstractmethod
from contextlib import suppress, AbstractContextManager
from enum import Enum
from typing import Mapping, Sequence, Union, Type

import attr
import dlestxetx
from crccheck.crc import CrcX25
from serial import Serial


class PageAnimate(Enum):
    """
    The :class:`PageAnimate` class holds constants
    for types of entry animations available to :class:`Pages <Page>`.

    Each constant has a string value
    which is used when converting :class:`Page` objects to & from strings.

    The documentation for each constant
    describes each available animation and any relevant considerations.
    """

    NONE = 'N'
    """
    Appear instantly.
    
    Text not fitting on the display is clipped and never seen.
    
    Page delay commences immediately.
    """

    VSCROLL = 'V'
    """
    Scroll vertically into view from the bottom,
    and remain on the display.
    
    Text not fitting on the display is clipped and never seen.
    
    Page delay commences as soon as the text is fully displayed.
    """

    HSCROLL = 'H'
    """
    Scroll horizontally into view from the right,
    simultaneously scrolling the previous page out of view to the left,
    then scroll out of view to the left.
    
    Page delay commences after all scrolling text becomes fully invisible,
    so usually a delay of ``0`` is desired in conjunction with :attr:`HSCROLL`.
    """


@attr.s(frozen=True)
class Page:
    # noinspection PyUnresolvedReferences
    """
    A :class:`Page` object represents one "screen" of information in a :class:`DisplayMessage`.

    Each :class:`Page` object holds the text to be displayed,
    how the text animates on entry,
    and how long the page should "pause"
    between completion of the animation and display of the next page.

    :class:`Page` objects are not typically constructed directly.
    Instead, they usually come to exist through construction of :class:`DisplayMessage` objects.

    :param animate:
        the type of animation to take place on page entry,
        given as a :class:`PageAnimate` constant.

    :param delay:
        the length of time (in approximately quarter-seconds)
        to delay display of the next page after animation completes,
        given as an :class:`int` between ``0`` and ``255`` inclusive.

    :param text:
        the text to display on the page.
        All ASCII letters & numbers,
        the ASCII space character,
        and these other printable ASCII characters
        can be used freely::

               (+)  (0)(1)(2)(3)(4)(5)(6)(7)(8)(9)(A)(B)(C)(D)(E)(F)

            (0x20)      !     #  $     &  '  (  )  *  +  ,  -  .  /
            (0x30)                                 :  ;  <  =  >  ?
            (0x50)                                       \\

        as well as some Unicode characters::

                 (+)  (0)(1)(2)(3)(4)(5)(6)(7)(8)(9)(A)(B)(C)(D)(E)(F)

            (0x00B0)                        ·
            (0x2020)         •
            (0x2500)   ─  ━
            (0x2580)                           █
            (0x2590)               ▔

        Notably, some printable ASCII characters **cannot** be used::

               (+)  (0)(1)(2)(3)(4)(5)(6)(7)(8)(9)(A)(B)(C)(D)(E)(F)

            (0x20)         "        %
            (0x40)   @
            (0x50)                                    [     ]  ^  _
            (0x60)   `
            (0x70)                                    {  |  }  ~  

        Some of these unusable characters are instead utilised for other purposes:

        *   Use ``~`` to right-justify the remaining text on the line.
        *   Use ``_`` to advance to the next line of the display.

        A few more of these characters
        are utilised by the various :class:`Page` & :class:`DisplayMessage` string methods
        to enable compact, easily-typed, pure-string representations containing all attributes.

    :raise ValueError:
        if the text contains unusable characters,
        or if a valid :class:`PageAnimate` value is not given,
        or if the delay is outside the permissible range.
    """
    animate: PageAnimate = attr.ib()
    delay: int = attr.ib()
    text: str = attr.ib()

    _TEXT_ENCODING: Mapping[str, bytes] = {
        **{
            char: bytes([ord(char)])
            for char in r" !#$&'()*+,-./0123456789:;<=>?ABCDEFGHIJKLMNOPQRSTUVWXYZ\abcdefghijklmnopqrstuvwxyz"
        },
        '\u00B7': b'\x8F',  # 'MIDDLE DOT'
        '\u2022': b'\xD3',  # 'BULLET'
        '\u2500': b'\x97',  # 'BOX DRAWINGS LIGHT HORIZONTAL'
        '\u2501': b'\xD2',  # 'BOX DRAWINGS HEAVY HORIZONTAL'
        '\u2588': b'\x5F',  # 'FULL BLOCK'
        '\u2594': b'\xA3',  # 'UPPER ONE EIGHTH BLOCK'
    }
    """
    A mapping from permissible ASCII/Unicode characters
    to the equivalent display-level byte.
    """

    _TEXT_DECODING: Mapping[bytes, str] = {
        **{byte: char for char, byte in _TEXT_ENCODING.items()},
        b'"': "'",
        # TODO: explore more of the super-0x80 byte space for potential variable-sized space mappings.
        b'\x98': '\u2500',
        b'\xA4': '\u2594',
        b'\xA5': '\u2594',
    }
    """
    A mapping from display-level bytes
    to the equivalent ASCII/Unicode character.
    
    In some cases, multiple display-level bytes map to a common ASCII/Unicode character:
    
    *   Bytes ``"`` and ``'`` map to character ``'``
        (which means ``"`` can't be permitted as an input character).
    *   Bytes ``\\xA3``, ``\\xA4``, and ``\\xA5`` map to character ``▔``.
    
    Although not problematic,
    this makes perfect round-tripping between characters and display bytes impossible,
    so it should never be assumed to be possible.
    """

    _ATTRS_SEP = '^'
    _RIGHT_CHAR_DECODED = '~'
    _RIGHT_CHAR_ENCODED = r'\R'
    _NEWLINE_CHAR = '_'
    _NEWLINE_BYTESEQ = b'\x0A'
    _STR_RE = re.compile(
        r'\A(?:(?P<animate>[A-Za-z]?)(?P<delay>\d*)' + re.escape(_ATTRS_SEP) + r')?(?P<text>.*)\Z',
        re.DOTALL
    )
    _ANIMATE_ENCODING: Mapping[PageAnimate, int] = {
        PageAnimate.NONE: 0x00,
        PageAnimate.VSCROLL: 0x1D,
        PageAnimate.HSCROLL: 0x2F,
    }
    _ANIMATE_DECODING: Mapping[int, PageAnimate] = {byte: animate for animate, byte in _ANIMATE_ENCODING.items()}

    @classmethod
    def from_str(cls, string: str, default_animate: PageAnimate = PageAnimate.NONE, default_delay: int = 20) -> 'Page':
        """
        Construct a :class:`Page` object from a string representation.

        :param string:
            a string in one of the following formats:

            *   ``<text>``
            *   ``^<text>``
            *   ``<animate>^<text>``
            *   ``<delay>^<text>``
            *   ``<animate><delay>^<text>``

            where:

            *   ``<animate>`` is the string value of the desired :class:`Animate` value
                (e.g. ``N`` for :attr:`Animate.NONE`);
            *   ``<delay>`` is the desired ``delay`` value; and
            *   ``<text>`` is the desired ``text`` value.

            For reference, such a string can also be obtained
            by converting an existing :class:`Page` object to a string using :class:`str() <str>`:

            >>> str(Page(animate=PageAnimate.VSCROLL, delay=40, text='12:34 FUNKYTOWN~5_Limited Express'))
            'V40^12:34 FUNKYTOWN~5_Limited Express'

        :param default_animate:
            the ``animate`` value to use if one is not provided in the string.
            Defaults to :attr:`PageAnimate.NONE`.

        :param default_delay:
            the ``delay`` value to use if one is not provided in the string.
            Defaults to ``20``.

        :raise ValueError:
            if the text contains unusable characters,
            or if a valid :class:`Animate` value is not given,
            or if the delay is outside the permissible range.
        """
        match = cls._STR_RE.match(string)
        if match.group('animate'):
            animate = PageAnimate(match.group('animate').upper())
        else:
            animate = default_animate
        if match.group('delay'):
            delay = int(match.group('delay'))
        else:
            delay = default_delay
        return Page(animate=animate, delay=delay, text=match.group('text'))

    @classmethod
    def from_bytes(cls, bytes_in: bytes) -> 'Page':
        """
        Construct a :class:`Page` object from a raw byte representation.

        Typically used by :meth:`DisplayMessage.from_bytes`
        when attempting to construct a :class:`DisplayMessage` from :class:`bytes`.

        :param bytes_in:
            the :class:`bytes` relating to one page.

        :raise ValueError:
            if the bytes could not be understood.
        """
        if len(bytes_in) < 4:
            raise ValueError('not enough bytes for a Page')
        try:
            animate = cls._ANIMATE_DECODING[bytes_in[0]]
        except KeyError:
            raise NotImplementedError(f'unexpected animate byte value {bytes_in[0]!r} at index 0')
        offset = bytes_in[1]
        delay = bytes_in[2]
        if bytes_in[3] != 0x00:
            raise NotImplementedError(f'unexpected byte value {bytes_in[3]!r} at index 3')
        text = cls._NEWLINE_CHAR.join(
            cls._decode_text(text_line).rstrip(' ').replace(cls._RIGHT_CHAR_ENCODED, cls._RIGHT_CHAR_DECODED)
            for text_line in bytes_in[4:].rstrip(cls._NEWLINE_BYTESEQ).split(cls._NEWLINE_BYTESEQ)
        )
        text = (cls._NEWLINE_CHAR * offset) + text
        return Page(animate=animate, delay=delay, text=text)

    def __str__(self) -> str:
        """
        The string representation of this object.

        Passing this string to :meth:`Page.from_str`
        will yield an equivalent :class:`Page` object to this one.
        """
        return self.animate.value + str(self.delay) + self._ATTRS_SEP + self.text

    def to_bytes(self) -> bytes:
        """
        The raw byte representation of the :class:`Page` as understood by the display.

        Used by :meth:`DisplayMessage.to_bytes`
        when preparing to :meth:`~PID.send()` a complete :class:`DisplayMessage` to the display.
        """
        animate_byte = bytes([self._ANIMATE_ENCODING[self.animate]])
        offset_byte = bytes([len(self.text) - len(self.text.lstrip(self._NEWLINE_CHAR))])
        delay_byte = bytes([self.delay])
        text_bytes = b'\x0A'.join(
            self._encode_text(text.replace(self._RIGHT_CHAR_DECODED, self._RIGHT_CHAR_ENCODED))
            for text in self.text[ord(offset_byte):].split(self._NEWLINE_CHAR)
        )
        return animate_byte + offset_byte + delay_byte + b'\x00' + text_bytes

    @classmethod
    def _encode_text(cls, text: str) -> bytes:
        """
        Convert a string of characters into a string of display-level bytes.
        Called from the :meth:`to_bytes` method.

        :param text:
            the string for display.

        :raise ValueError:
            if any of the characters in the input are unable to be displayed.
        """
        bytes_out = bytes()
        bad_chars = set()
        for char in text:
            try:
                bytes_out += cls._TEXT_ENCODING[char]
            except KeyError:
                bad_chars.add(char)
        if bad_chars:
            raise ValueError(
                f"{', '.join(repr(char) for char in bad_chars)} not in allowed characters"
                f" ({repr(''.join(cls._TEXT_ENCODING.keys()))})"
            )
        return bytes_out

    @classmethod
    def _decode_text(cls, bytes_in: bytes) -> str:
        """
        Convert a string of display-level bytes into a string of characters.
        Any byte without a corresponding character
        is converted to the Unicode "Replacement Character" (``�``).
        Called from the :meth:`Page.from_bytes` method.

        :param bytes_in:
            the display-level bytes.
        """
        text: str = ''
        for byte in (bytes([int_in]) for int_in in bytes_in):
            try:
                text += cls._TEXT_DECODING[byte]
            except KeyError:
                text += '\N{REPLACEMENT CHARACTER}'
        return text


class Message(ABC):
    """
    The :class:`Message` class is an :term:`abstract base class`
    of the :class:`DisplayMessage`, :class:`PingMessage`, and :class:`ResponseMessage` classes.
    Its existence allows for simplified implementation & return typing of the :func:`inspect` function.
    """

    @classmethod
    @abstractmethod
    def marker(cls) -> bytes:
        """
        The :class:`bytes` that a raw byte representation must start with
        in order to possibly be an instance of this :class:`Message` subclass.
        """

    @classmethod
    @abstractmethod
    def from_bytes(cls, bytes_in: bytes) -> 'Message':
        """
        Construct an instance of this :class:`Message` subclass from a raw byte representation
        (not including the CRC-checksumming and packet-framing required for transmission).
        """

    @abstractmethod
    def to_bytes(self) -> bytes:
        """
        Construct a raw byte representation of this :class:`Message` subclass
        (not including the CRC-checksumming and packet-framing required for transmission).
        """


@attr.s(frozen=True)
class PingMessage(Message):
    # noinspection PyUnresolvedReferences
    """
    A :class:`PingMessage` exists as :class:`Message` to send to the display with no visual effect,
    but which impedes the automatic clearing of the display
    (which otherwise occurs after approximately one minute of inactivity).

    :class:`PingMessage` objects are exclusively constructed and sent by the :meth:`PID.ping` method,
    but they exist as a class in case their raw byte representations are passed to the :func:`inspect` function.

    :param unspecified_byte:
        a byte that seems to have no effect if changed,
        but in deployment is typically ``0x6F``.
    """

    unspecified_byte: int = attr.ib(default=0x6F)

    @classmethod
    def marker(cls) -> bytes:
        return b'\x01\x50'

    @classmethod
    def from_bytes(cls, bytes_in: bytes) -> 'PingMessage':
        if not bytes_in.startswith(cls.marker()):
            raise ValueError('incorrect header for PingMessage')
        if len(bytes_in) < 3:
            raise ValueError('unexpected end of data')
        if len(bytes_in) > 3:
            raise ValueError('unexpected data')
        return PingMessage(unspecified_byte=bytes_in[2])

    def to_bytes(self) -> bytes:
        return self.marker() + bytes([self.unspecified_byte])


@attr.s(frozen=True)
class ResponseMessage(Message):
    # noinspection PyUnresolvedReferences
    """
    A :class:`ResponseMessage` represents a response received from the display
    after a transmission to it.

    :class:`ResponseMessage` objects are not intended to be sent to the display.
    They exist as a class in order to be recognised by the :func:`inspect` function,
    which is used internally by :meth:`PID.send` to verify acknowledgement from the display
    following the sending of a message.

    :param unspecified_byte:
        a variable byte that usually somewhat seems to be related
        to the ``unspecified_byte`` value of the previously-sent :class:`PingMessage`,
        but not always, so it is captured but otherwise ignored.
    """

    unspecified_byte: int = attr.ib()

    @classmethod
    def marker(cls) -> bytes:
        return b'\x01\x52'

    @classmethod
    def from_bytes(cls, bytes_in: bytes) -> 'ResponseMessage':
        if not bytes_in.startswith(cls.marker()):
            raise ValueError('incorrect header for ResponseMessage')
        if len(bytes_in) < 4:
            raise ValueError('unexpected end of data')
        if len(bytes_in) > 4:
            raise ValueError('unexpected data')
        if not bytes_in.endswith(b'\x00'):
            raise ValueError('unexpected value at offset 3: {!r}'.format(bytes([bytes_in[-1]])))
        return ResponseMessage(unspecified_byte=bytes_in[2])

    def to_bytes(self) -> bytes:
        return self.marker() + bytes([self.unspecified_byte]) + b'\x00'


@attr.s(frozen=True, repr=False)
class DisplayMessage(Message):
    # noinspection PyUnresolvedReferences
    """
    A :class:`DisplayMessage` object represents a single, cohesive set of information
    displayed over a sequence of :class:`Pages <Page>`.
    Once the sequence is exhausted, it repeats indefinitely
    until a new message is sent to the display
    (or the display times out & clears,
    which can be avoided by :meth:`~PID.ping`-ing the display).

    :class:`DisplayMessage` objects are typically built from a string using :meth:`DisplayMessage.from_str`
    rather than constructed directly.

    :param pages:
        a :class:`tuple` of :class:`Page` objects comprising the message.
    """
    pages: Sequence[Page] = attr.ib(converter=tuple)

    _PAGE_SEP = '|'

    @classmethod
    def marker(cls) -> bytes:
        return b'\x01\x44\x00'

    @classmethod
    def from_str(cls, string: str) -> 'DisplayMessage':
        """
        Construct a :class:`DisplayMessage` object from a string representation.
        
        :param string:
            a string in one of the following formats:

            *   ``<page_str>``
            *   ``<page_str>|<page_str>``
            *   ``<page_str>|<page_str>|<page_str>``

                *(etc.)*

            where each ``<page_str>`` is a string representation of a :class:`Page` object,
            as accepted by :meth:`Page.from_str`,
            and is separated from other :class:`Page` representations by ``|``.

            For reference, such a string can also be obtained
            by converting an existing :class:`DisplayMessage` object to a string
            using :class:`str() <str>`:

            >>> page1 = Page(animate=PageAnimate.VSCROLL, delay=40, text='12:34 FUNKYTOWN~5_Limited Express')
            >>> page2 = Page(animate=PageAnimate.HSCROLL, delay=0, text='_Stops all stations except East Richard')
            >>> str(DisplayMessage([page1, page2]))
            'V40^12:34 FUNKYTOWN~5_Limited Express|H0^_Stops all stations except East Richard'

            Where any page string fails to specify an ``animate`` or ``delay`` value,
            these defaults will be applied:

            *   :attr:`Animate.VSCROLL` & ``delay=40`` for the first page; and
            *   :attr:`Animate.HSCROLL` & ``delay=0`` for subsequent pages.

        :raise ValueError:
            if the text of any page contains unusable characters,
            or if a valid Animate value is not given,
            or if the delay is outside the permissible range.
        """
        return DisplayMessage(pages=tuple(
            Page.from_str(
                string=page_str,
                default_delay=40 if index == 0 else 0,
                default_animate=PageAnimate.VSCROLL if index == 0 else PageAnimate.HSCROLL
            )
            for index, page_str in enumerate(string.split(cls._PAGE_SEP))
        ))

    @classmethod
    def from_bytes(cls, bytes_in: bytes) -> 'DisplayMessage':
        """
        Construct a :class:`DisplayMessage` object from a raw byte representation
        (not including the CRC-checksumming and packet-framing required for transmission).

        :param bytes_in:
            the raw byte representation.

        :raise ValueError:
            if the bytes could not be understood.
        """
        if not bytes_in.startswith(cls.marker()):
            raise ValueError(f'data must start with {cls.marker()!r}')
        index = len(cls.marker())
        pages = []
        while True:
            if pages:
                if bytes_in[index] != 0x01:
                    raise ValueError(f'unexpected byte value {bytes_in[index]!r} at index {index}')
                index += 1
            try:
                end = bytes_in.index(b'\x0D', index)
            except ValueError:
                raise ValueError('unexpected end of data')
            pages.append(Page.from_bytes(bytes_in[index:end]))
            index = end + 1
            if index == len(bytes_in):
                break
        return DisplayMessage(pages=pages)

    def __str__(self) -> str:
        """
        The string representation of this object.

        Passing this string to :meth:`DisplayMessage.from_str`
        will yield an equivalent :class:`DisplayMessage` object to this one.
        """
        return self._PAGE_SEP.join([str(page) for page in self.pages])

    def to_bytes(self) -> bytes:
        """
        The raw byte representation of the :class:`DisplayMessage` as understood by the display
        (not including the CRC-checksumming and packet-framing required for transmission).
        """
        return self.marker() + b'\x0D\x01'.join(page.to_bytes() for page in self.pages) + b'\x0D'

    def __repr__(self) -> str:
        return 'DisplayMessage.from_str({!r})'.format(str(self))


@attr.s(frozen=True)
class PID(AbstractContextManager):
    # noinspection PyUnresolvedReferences
    """
    A :class:`PID` object represents a serial connection to a physical display.

    :class:`PID` objects are typically constructed using the :meth:`PID.for_device` class method,
    and can send messages in the form of :class:`Message` objects, strings, or raw :class:`bytes`
    using the :meth:`send` method.
    It is possible to :meth:`ping` the display at regular intervals
    to persist the currently-displayed message.

    :class:`PID` objects also manage the CRC checksumming & DLE/STX/ETX packet framing
    used by the display in what it receives & transmits,
    and ensure that every instruction sent to the display
    is acknowledged.

    :class:`PID` objects are :ref:`context managers <context-managers>`,
    enabling automatic closing of the underlying :class:`~serial.Serial` connection
    when used in a ``with`` block::

        with PID.for_device(...) as pid:
            pid.send(...)

        # serial connection will never be open at this point

    :param serial:
        a :class:`serial.Serial` object.
        In normal use a correctly configured one
        is set by :meth:`PID.for_device`.

    :param ignore_responses:
        whether to ignore the response from the PID
        whenever :meth:`PID.send` is called.
        Defaults to ``False``.

    """

    serial: Serial = attr.ib()
    ignore_responses: bool = attr.ib(False)

    @classmethod
    def for_device(cls, port: str, ignore_responses: bool = False) -> 'PID':
        """
        Construct a :class:`PID` object connected to the specified serial device
        with a correctly configured :class:`serial.Serial` object.

        The :class:`~serial.Serial` object is configured to time out after 500ms
        during read operations,
        which is ample time for the display to send acknowledgement
        after being written to.

        :param port:
            the serial device name,
            such as ``/dev/ttyUSB0`` on Linux or ``COM1`` on Windows.
            The correct device name can be found on Linux
            by unplugging and re-plugging the display connection,
            running ``dmesg``,
            and inspecting the output for the device name.

        :param ignore_responses:
            whether to ignore the response from the PID
            whenever :meth:`PID.send` is called.
            Defaults to ``False``.

        :raise serial.SerialException:
            if the serial device can't be found or can't be configured.
        """
        return PID(serial=Serial(port=port, timeout=0.5), ignore_responses=ignore_responses)

    def send(self, data: Union[str, Message, bytes]) -> None:
        """
        Send data to the display---most typically message data,
        although any :class:`bytes` data can be sent.

        *   If a string is provided,
            it is converted to a :class:`DisplayMessage` object using :meth:`DisplayMessage.from_str`,
            then :meth:`~DisplayMessage.to_bytes`,
            then CRC-checksummed and packet-framed before sending.
        *   If a :class:`Message` object is provided
            (usually a :class:`DisplayMessage` but sometimes a :class:`PingMessage`),
            it is converted :meth:`~Message.to_bytes`,
            then CRC-checksummed and packet-framed before sending.
        *   If a :class:`bytes` object is provided that **is not** a valid DLE/STX/ETX packet
            (``\\x10\\x02 ··· \\x10\\x03``),
            the bytes are CRC-checksummed and packet-framed before sending.
        *   If a :class:`bytes` object is provided that **is** a valid DLE/STX/ETX packet,
            the packet is assumed to already contain a correct CRC checksum
            and sent without change.

        :param data:
            a string, :class:`Message` object, or :class:`bytes` object.

        :raise serial.SerialTimeoutException:
            if the display doesn't respond with acknowledgement.

        :raise serial.SerialException:
            if any other serial device error occurs,
            such as the serial port being closed.
        """
        if isinstance(data, str):
            data = DisplayMessage.from_str(data)
        if isinstance(data, Message):
            data = data.to_bytes()
        # noinspection PyUnusedLocal
        is_framed = False
        with suppress(ValueError):
            dlestxetx.decode(data)
            is_framed = True
        if not is_framed:
            data = dlestxetx.encode(data + _crc(data))
        self.serial.write(data)
        if not self.ignore_responses:
            response = _uncrc(dlestxetx.read(self.serial))
            if self.serial.in_waiting:
                raise NotImplementedError('more data came back from the PID device than expected')
            if not isinstance(inspect(response), ResponseMessage):
                raise NotImplementedError('unexpected response from the PID device: {!r}'.format(response))

    def ping(self) -> None:
        """
        "Ping" the display,
        which has no direct visual effect
        but impedes the automatic clearing of the display
        (which otherwise occurs after approximately one minute of inactivity).

        In deployment, Metlink displays are typically pinged every ten seconds
        in addition to all other traffic sent to them.

        This method is simply a convenience wrapper for :meth:`send`-ing a :class:`PingMessage`::

            pid.send(PingMessage())

        :raise serial.SerialTimeoutException:
            if the display doesn't respond with acknowledgement.

        :raise serial.SerialException:
            if any other serial device error occurs,
            such as the serial port being closed.
        """
        self.send(PingMessage())

    def close(self) -> None:
        """
        Close the underlying :class:`~serial.Serial` connection.

        Called automatically when the :class:`PID` object is used in a ``with`` block::

            with PID.for_device(...) as pid:
                pid.send(...)

            # serial connection will never be open at this point
        """
        self.serial.close()

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """
        Ensure that the underlying :class:`~serial.Serial` connection is closed.
        Called at the end of any ``with`` block that uses this :class:`PID` object.

        The parameters describe the exception raised inside the ``with`` block, if any,
        and are not used.

        :return:
            ``False``,
            to indicate that any exception that occurred
            should propagate to the caller rather than be suppressed.
        """
        self.close()
        return False


def inspect(bytes_in: bytes) -> Message:
    """
    The :func:`inspect` function is used
    to determine how the display would interpret an arbitrary sequence of bytes.

    It de-frames & CRC-checks the data (if a DLE/STX/ETX packet is provided),
    then compares the header against the headers of all known :class:`Message` types,
    then constructs an object of the matching type.

    The :func:`inspect` function is used internally by :meth:`PID.send`
    to ensure that a valid :class:`ResponseMessage` is received after each transmission.

    :return:
        a :class:`DisplayMessage` object,
        a :class:`PingMessage` object,
        or a :class:`ResponseMessage` object.

    :raise ValueError:
        if a DLE/STX/ETX packet is provided with a bad CRC checksum,
        or if the bytes can't be understood.
    """
    # noinspection PyUnusedLocal
    was_framed = False
    with suppress(ValueError):
        bytes_in = dlestxetx.decode(bytes_in)
        was_framed = True
    if was_framed:
        bytes_in = _uncrc(bytes_in)
    # noinspection PyUnusedLocal
    cls: Type[Message]
    for cls in Message.__subclasses__():
        if bytes_in.startswith(cls.marker()):
            return cls.from_bytes(bytes_in)
    raise ValueError('unrecognised byte sequence')


def _crc(bytes_in: bytes) -> bytes:
    """
    Generate an X.25_ checksum for the specified byte sequence.

    ..  _X.25:
        https://en.wikipedia.org/wiki/X.25

    :param bytes_in:
        the bytes to generate the checksum for.

    :return:
        a two-byte :class:`bytes` sequence in the order expected by the display.
    """
    return struct.pack('<H', CrcX25.calc(bytes_in))


def _uncrc(bytes_in: bytes) -> bytes:
    """
    Verify the validity of the specified byte sequence,
    which ends with a two-byte CRC checksum as generated by :func:`_crc`,
    and discard the checksum.

    :param bytes_in:
        the bytes with checksum to verify.

    :return:
        the verified byte sequence without the checksum.

    :raise ValueError:
        if the checksum verification fails.
    """
    if len(bytes_in) < 2:
        raise ValueError('value must be at least 2 bytes in length')
    bytes_out, crc_in = bytes_in[:-2], bytes_in[-2:]
    crc_out = _crc(bytes_out)
    if crc_in != crc_out:
        raise ValueError(f'got CRC value {crc_in!r} when {crc_out!r} was expected')
    return bytes_out
