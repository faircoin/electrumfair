Electrum - Lightweight FairCoin client
======================================

::

  Licence: MIT Licence
  Author: Thomas König
  Original Author: Thomas Voegtlin
  Language: Python (>= 3.6)
  Homepage: https://download.faircoin.world/


Getting started
===============

Electrum is a pure python application. If you want to use the
Qt interface, install the Qt dependencies::

    sudo apt-get install python3-pyqt5

If you downloaded the official package (tar.gz), you can run
Electrum from its root directory without installing it on your
system; all the python dependencies are included in the 'packages'
directory. To run Electrum from its root directory, just do::

    ./run_electrumfair

You can also install Electrum on your system, by running this command::

    sudo apt-get install python3-setuptools
    python3 -m pip install .[fast]

This will download and install the Python dependencies used by
Electrum instead of using the 'packages' directory.
The 'fast' extra contains some optional dependencies that we think
are often useful but they are not strictly needed.

If you cloned the git repository, you need to compile extra files
before you can run Electrum. Read the next section, "Development
Version".



Development version
===================

Check out the code from GitHub::

    git clone git://github.com/faircoin/electrumfair.git
    cd electrumfair

Run install (this should install dependencies)::

    python3 -m pip install .[fast]


Compile the protobuf description file::

    sudo apt-get install protobuf-compiler
    protoc --proto_path=electrumfair --python_out=electrumfair electrumfair/paymentrequest.proto


Install on Linux systems
========================

If you install Electrum on your system, you can run it from any
directory.

If you have pip, you can do::

    python3 setup.py sdist
    sudo pip3 install --pre dist/ElectrumFair-3.3.4.tar.gz


If you don't have pip, install with::

    python3 setup.py sdist
    sudo python3 setup.py install



Creating Binaries
=================

Linux
-----

See :code:`contrib/build-linux/README.md`.


Mac OS X / macOS
----------------

See :code:`contrib/osx/README.md`.



Windows
-------

See :code:`contrib/build-wine/docker/README.md`.


Android
-------

See :code:`contrib/android/Readme.md`.
