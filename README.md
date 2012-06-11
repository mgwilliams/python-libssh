python-libssh
=============

python-libssh is a Python wrapper for the [libssh](http://www.libssh.org) C library. 
It is implemented using the ctypes module from stdlib.

__Warning:__ This code is in early alpha and may produce unexpected results. Please use with caution.

Example Usage
=============

```python
import stat
import os

from libssh import *

# open an SSH session to 'smart.host.com'
ssh = SshSession('smart.host.com', 'ubuntu', password='password')

# or, for public key authentication
# ssh = SshSession('smart.host.com', 'ubuntu')

channel = ssh.get_channel()
channel.execute_command("whoami")
channel.read()
channel.close()

channel = ssh.get_channel()
channel.execute_sudo_command("whoami")
channel.read()
channel.close()

sftp = SftpSession(ssh)
f = sftp.open("foo.txt", (os.O_WRONLY | os.O_CREAT | os.O_TRUNC), stat.S_IRWXU)
f.write("hello world")
f.close()
sftp.close()

```

Author
======

Matthew Williams -- mgwilliams@gmail.com
