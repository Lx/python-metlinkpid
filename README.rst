################################################################
``metlinkpid``: Metlink LED passenger information display driver
################################################################

The ``metlinkpid`` module provides a class to operate Metlink LED passenger information displays:

>>> from metlinkpid import PID
>>> with PID.for_device('/dev/ttyUSB0') as pid:
...     pid.send('12:34 FUNKYTOWN~5_Limited Express|_Stops all stations except East Richard')

It also provides a function to inspect raw display data,
both with and without checksumming & packet-framing:

>>> from metlinkpid import inspect
>>> inspect(b'\x10\x02\x01\x44\x00\x1D\x00\x00\x00\x4F\x50\x45\x4E\x0A\x46\x4F\x52\x20\x42\x55\x53\x49\x4E\x45\x53\x53\x0D\x8F\xDF\x10\x03')
DisplayMessage.from_str('V0^OPEN_FOR BUSINESS')
>>> inspect(b'\x01\x44\x00\x1D\x00\x00\x00\x53\x54\x49\x4C\x4C\x20\x4F\x50\x45\x4E\x0A\x46\x4F\x52\x20\x42\x55\x53\x49\x4E\x45\x53\x53\x0D')
DisplayMessage.from_str('V0^STILL OPEN_FOR BUSINESS')
>>> inspect(b'\x01\x50\x6F')
PingMessage(unspecified_byte=111)


Installation
============

Install from PyPI_ using pip_::

    pip install metlinkpid

..  _PyPI: https://pypi.org/project/metlinkpid
..  _pip: https://pip.pypa.io/


Basic usage
===========

Find the device
---------------

Determine the device to which the display is connected.
On Linux, this can be achieved by disconnecting the display from the computer & reconnecting,
then inspecting the contents of ``dmesg`` output for USB attachment messages::

    [    3.010816] usb 1-1.4: FTDI USB Serial Device converter now attached to ttyUSB0

The above output indicates that the display is reachable through ``/dev/ttyUSB0``.

Display a message
-----------------

Next, write & run a Python script
that connects to that device location
and calls ``PID.send()``::

    from metlinkpid import PID
    with PID.for_device('/dev/ttyUSB0') as pid:
        pid.send('12:34 FUNKYTOWN~5_Limited Express|_Stops all stations except East Richard')

The PID should display the specified message instantly,
but after approximately one minute the display will self-clear.

Keep the message up
-------------------

To prevent the message from clearing,
the display can be *pinged* at a regular interval::

    from time import sleep

    from metlinkpid import PID
    with PID.for_device('/dev/ttyUSB0') as pid:
        pid.send('12:34 FUNKYTOWN~5_Limited Express|_Stops all stations except East Richard')

        while True:
            sleep(10)
            pid.ping()


Message format
--------------

Use the ``|`` character to separate *pages* of a message::

    pid.send('V10^FIRST_PAGE|V10^SECOND_PAGE|V10^THIRD_PAGE')

The message in the above ``send()`` call has three pages:
``V10^FIRST_PAGE``, ``V10^SECOND_PAGE``, and ``V10^THIRD_PAGE``.

Page format
-----------

Everything in a page up to and including the ``^`` affects the display of the page,
and is not included in the output.
The letter specifies the *animation* and can be ``V`` for a vertical upwards scroll,
``H`` for a horizontal scroll,
or ``N`` for no animation.
The number specifies the *delay* (in roughly quarter-seconds)
after the animation finishes and before the next page (or first page again) is shown.

Text after ``~`` will be right-aligned on the current line,
and text after ``_`` will appear on the next line.
Each page in the above example therefore spans two lines.

Some ASCII characters *are not* available for display,
and some "extended" Unicode characters *are* available.
Full details are in the `documentation`_ for the ``Page`` class.

..  _documentation:
    https://python-metlinkpid.readthedocs.io/en/latest/classes/page.html


Known issues
============

Animation types
    Not all known page animation types are implemented yet.

``PID`` class unit testing
    Unit tests have not yet been written for the ``PID`` class.
    A suitable serial port mocking interface is yet to be found.


Support
=======

The ``metlinkpid`` module is fully documented.
All further usage & development details can be found in the documentation.
Bug reports, feature requests, and questions are welcome via the issue tracker.

:Documentation: https://python-metlinkpid.readthedocs.io
:Issue tracker: https://github.com/Lx/python-metlinkpid/issues


Contribute
==========

Pull requests for both code and documentation improvements
are gratefully received and considered.

:GitHub repository: https://github.com/Lx/python-metlinkpid


License
=======

This project is licensed under the `MIT License`_.

..  _MIT License: https://opensource.org/licenses/MIT
