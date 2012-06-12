#from clibssh import *
import select
import os
import os.path
import random
import pipes
import time
import ctypes

import clibssh

def splitpath(path, maxdepth=20):
    ( head, tail ) = os.path.split(path)
    return splitpath(head, maxdepth - 1) + [ tail ] \
        if maxdepth and head and head != path \
        else [ head or tail ]


class SshObject(object):
    pass


class SshPoller(SshObject):
    def __init__(self):
        self.session_map = {}
        self.poller = select.poll()

    def register(self, session):
        fd = session.fileno()
        self.session_map[fd] = session
        self.poller.register(fd, select.POLLIN)

    def poll(self, timeout=None):
        readable_fds = self.poller.poll(timeout)
        readables = []
        for i in readable_fds:
            readables.append(self.session_map[i[0]])
        return readables


class SshSession(SshObject):
    def __init__(self, host=None, user=None, port=None, password=None, session=None):
        if not session:
            session = clibssh.ssh_new()
            clibssh.ssh_options_set(session, clibssh.SSH_OPTIONS_HOST, host)
            if port:
                clibssh.ssh_options_set(session, clibssh.SSH_OPTIONS_PORT, port)
            if user:
                clibssh.ssh_options_set(session, clibssh.SSH_OPTIONS_USER, user)
            clibssh.ssh_options_set(session, clibssh.SSH_OPTIONS_COMPRESSION, 'none')

            clibssh.ssh_connect(session)

            if password:
                clibssh.ssh_userauth_password(session, None, password)
            else:
                clibssh.ssh_userauth_autopubkey(session, None)
        self.session = session
        fd = self.fileno()
        if fd < 0:
            self.connected = False
            return
        self.connected = True
        self.channels = []
        self.sudo_marker = None

    def fileno(self):
        return clibssh.ssh_get_fd(self.session)

    def readable_channels(self, stderr=False):
        readable = []
        for channel in self.channels:
            if channel.poll(stderr) > 0:
                readable.append(channel)
        return readable

    def get_channel(self):
        channel = SshChannel(self)
        self.channels.append(channel)
        return channel

    def print_error(self, msg):
        err = clibssh.ssh_get_error(self.session)
        print "%s: %s" % (msg, err)

    def put_file(self, remote_path, data, mode):
        remote_path = str(remote_path)
        path, filename = os.path.split(remote_path)

        scp = clibssh.ssh_scp_new(self.session, (clibssh.SSH_SCP_WRITE), path)
        if clibssh.ssh_scp_init(scp) != clibssh.SSH_OK:
            self.print_error("Cannot open scp session")
        clibssh.ssh_scp_close(scp)
        clibssh.ssh_scp_free(scp)

        scp = clibssh.ssh_scp_new(self.session, (clibssh.SSH_SCP_WRITE), path)
        if clibssh.ssh_scp_init(scp) != clibssh.SSH_OK:
            self.print_error("Cannot open scp session")
            return
        rc = clibssh.ssh_scp_push_file(scp, filename, len(data), mode)
        if rc != clibssh.SSH_OK:
            self.print_error("Cannot open remote file for writing")
            return
        if len(data):
            rc = clibssh.ssh_scp_write(scp, data, len(data))
            if rc != clibssh.SSH_OK:
                self.print_error("Cannot write to remote file")
        clibssh.ssh_scp_close(scp)
        clibssh.ssh_scp_free(scp)
        print "done"
        return clibssh.SSH_OK

class SshChannel(SshObject):
    def __init__(self, session):
        channel = clibssh.ssh_channel_new(session.session)
        clibssh.ssh_channel_open_session(channel)
        self.channel = channel
        self.session = session
        self.reader, self.writer = os.pipe()
        self.sudo = False
        self.poller = select.poll()
        self.poller.register(session.fileno())

    def poll(self, stderr=False):
        stderr = int(stderr)
        return clibssh.ssh_channel_poll(self.channel, stderr)

    def read(self, stderr=False):
        data = ''
        n = 0
        bufflen = self.poll(stderr)
        stderr = int(stderr)
        while bufflen != clibssh.SSH_EOF:
            if bufflen > 0:
                buff = ctypes.create_string_buffer(bufflen)
                n2 = clibssh.ssh_channel_read(self.channel, buff, bufflen, stderr)
                n = n + n2
                data = data + buff.value
                if self.sudo and self.session.sudo_marker in data:
                    break
            
            self.poller.poll()
            time.sleep(0.01)
            bufflen = self.poll(stderr)

        if self.sudo:
            data = data[:data.find(self.session.sudo_marker)]
            data = data.strip(' \t\n\r')
        return data, n

    def execute_command(self, command):
        clibssh.ssh_channel_request_exec(self.channel, command)

    def execute_sudo_command(self, command, password=None, user='root'):
        rc = clibssh.ssh_channel_request_pty(self.channel)
        rc = clibssh.ssh_channel_request_shell(self.channel)
        if not self.session.sudo_marker:
            sudo_marker = ''.join(chr(random.randint(ord('a'), ord('z'))) for x in xrange(32))
        else:
            sudo_marker = self.session.sudo_marker
        prompt = '[sudo via libssh, key=%s] password: ' % sudo_marker
        sudocmd = 'sudo -k && sudo -p "%s" -u %s -- "$SHELL" -c %s; echo %s\n' % (
            prompt, user, pipes.quote(command), sudo_marker)
        self.session.sudo_marker = sudo_marker
        sudo_output = ''
        clibssh.ssh_channel_write(self.channel, sudocmd, len(bytes(sudocmd)))
        
        if password:
            while not sudo_output.endswith(prompt):
                bufflen = self.poll()
                if bufflen>0:
                    buff = ctypes.create_string_buffer(bufflen)
                    n = clibssh.ssh_channel_read(self.channel, buff, bufflen, 0)
                    sudo_output += buff.value
                time.sleep(0.01)
            password = password + '\n'
            clibssh.ssh_channel_write(self.channel, password, len(bytes(password)))
        self.sudo=True

    def close(self):
        clibssh.ssh_channel_close(self.channel)
        clibssh.ssh_channel_send_eof(self.channel)
        clibssh.ssh_channel_free(self.channel)



class SftpSession(SshObject):
    def __init__(self, session):
        sftp = clibssh.sftp_new(session.session)
        rc = clibssh.sftp_init(sftp)
        self.sftp = sftp
        self.session = session

    def open(self, path, access_type, mode):
        file = SftpFile(self, path, access_type, mode)
        return file

    def close(self):
        clibssh.sftp_free(self.sftp)

class SftpFile(SshObject):
    def __init__(self, session, path, access_type, mode):
        self.session = session
        self.file = clibssh.sftp_open(session.sftp, path, access_type, mode)

    def write(self, data):
        rc = clibssh.sftp_write(self.file, bytes(data), len(bytes(data)))
        err = clibssh.ssh_get_error(self.session.session.session)
        return rc

    def read(self, dest):
        f = file(dest, 'wb')
        bufflen = 2048
        buff = ctypes.create_string_buffer(bufflen)
        n = clibssh.sftp_read(self.file, buff, bufflen)
        while n > 0:
           f.write(buff.value)
           n = clibssh.sftp_read(self.file, buff, bufflen)
        f.close()

    def close(self):
        rc = clibssh.sftp_close(self.file)


class ScpSession(SshObject):
    def __init__(self, session):
        self.        rc = clibssh.ssh_scp_init(self.scp)
        self.session = session

    def __dealloc__(self):
        scp_close(self.scp)
        scp_free(self.scp)
    
