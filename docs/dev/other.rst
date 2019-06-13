Other Classes & Methods
=======================

Knowledge of the following classes, methods, constants, and functions
is only of benefit to those who wish to better understand the internals of the ``metlinkpid`` module.


:class:`~metlinkpid.Message` Class
----------------------------------

..  autoclass:: metlinkpid.Message

    ..  automethod:: marker
    ..  automethod:: from_bytes
    ..  automethod:: to_bytes


:class:`~metlinkpid.PingMessage` Class
--------------------------------------

..  autoclass:: metlinkpid.PingMessage

    ..  automethod:: from_bytes
    ..  automethod:: to_bytes


:class:`~metlinkpid.ResponseMessage` Class
------------------------------------------

..  autoclass:: metlinkpid.ResponseMessage

    ..  automethod:: from_bytes
    ..  automethod:: to_bytes


Private :class:`~metlinkpid.Page` Methods & Constants
-----------------------------------------------------

:meth:`~metlinkpid.Page._encode_text` Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

..  automethod:: metlinkpid.Page._encode_text

:attr:`~metlinkpid.Page._TEXT_ENCODING` Constant
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

..  autoattribute:: metlinkpid.Page._TEXT_ENCODING

:meth:`~metlinkpid.Page._decode_text` Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

..  automethod:: metlinkpid.Page._decode_text

:attr:`~metlinkpid.Page._TEXT_DECODING` Constant
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

..  autoattribute:: metlinkpid.Page._TEXT_DECODING


Private :func:`~metlinkpid._crc` Function
-----------------------------------------

..  autofunction:: metlinkpid._crc


Private :func:`~metlinkpid._uncrc` Function
-------------------------------------------

..  autofunction:: metlinkpid._uncrc
