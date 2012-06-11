from clibssh import *
import select
import os
import os.path
import random
import pipes
import time


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
            session = ssh_new()
            ssh_options_set(session, SSH_OPTIONS_HOST, host)
            if port:
                ssh_options_set(session, SSH_OPTIONS_PORT, port)
            if user:
                ssh_options_set(session, SSH_OPTIONS_USER, user)
            ssh_options_set(session, SSH_OPTIONS_COMPRESSION, 'none')

            ssh_connect(session)

            if password:
                ssh_userauth_password(session, NULL, password)
            else:
                ssh_userauth_autopubkey(session, NULL)
        self.session = session
        fd = self.fileno()
        if fd < 0:
            self.connected = False
            return
        self.connected = True
        self.channels = []
        self.sudo_marker = None

    def fileno(self):
        return ssh_get_fd(self.session)

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
        err = ssh_get_error(self.session)
        print "%s: %s" % (msg, err)

    def put_file(self, remote_path, data, mode):
        path, filename = os.path.split(remote_path)
        channel = SshChannel(self)
        channel.execute_command("mkdir -p %s" % path)
        channel.close()
 
        scp = ssh_scp_new(self.session, SSH_SCP_WRITE | SSH_SCP_RECURSIVE, '.')
        if ssh_scp_init(scp) != SSH_OK:
            self.print_error("Cannot open scp session")
            return

        print "entering dir: ", path

        rc = ssh_scp_push_directory(scp, c_char_p(path), mode)
        if rc != SSH_OK:
            self.print_error("Could not enter directory")
        rc = ssh_scp_push_file(scp, c_char_p(filename), len(data), mode)
        if rc != SSH_OK:
            self.print_error("Cannot open remote file for writing")
            return

        rc = ssh_scp_write(scp, c_char_p(data), len(data))
        if rc != SSH_OK:
            self.print_error("Cannot write to remote file")
        ssh_scp_close(scp)
        ssh_scp_free(scp)
        return SSH_OK

class SshChannel(SshObject):
    def __init__(self, session):
        channel = ssh_channel_new(session.session)
        ssh_channel_open_session(channel)
        self.channel = channel
        self.session = session
        self.reader, self.writer = os.pipe()
        self.sudo = False
        self.poller = select.poll()
        self.poller.register(session.fileno())

    def poll(self, stderr=False):
        stderr = int(stderr)
        return ssh_channel_poll(self.channel, stderr)

    def read(self, stderr=False):
        data = ''
        n = 0
        bufflen = self.poll(stderr)
        stderr = int(stderr)
        while bufflen != SSH_EOF:
            if bufflen > 0:
                buff = create_string_buffer(bufflen)
                n2 = ssh_channel_read(self.channel, buff, bufflen, stderr)
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
        command = c_char_p(command)
        ssh_channel_request_exec(self.channel, command)

    def execute_sudo_command(self, command, password=None, user='root'):
        rc = ssh_channel_request_pty(self.channel)
        rc = ssh_channel_request_shell(self.channel)
        if not self.session.sudo_marker:
            sudo_marker = ''.join(chr(random.randint(ord('a'), ord('z'))) for x in xrange(32))
        else:
            sudo_marker = self.session.sudo_marker
        prompt = '[sudo via ansible, key=%s] password: ' % sudo_marker
        sudocmd = 'sudo -k && sudo -p "%s" -u %s -- "$SHELL" -c %s; echo %s\n' % (
            prompt, user, pipes.quote(command), sudo_marker)
        self.session.sudo_marker = sudo_marker
        sudo_output = ''
        ssh_channel_write(self.channel, c_char_p(sudocmd), len(bytes(sudocmd)))
        
        if password:
            while not sudo_output.endswith(prompt):
                bufflen = self.poll()
                if bufflen>0:
                    buff = create_string_buffer(bufflen)
                    n = ssh_channel_read(self.channel, buff, bufflen, 0)
                    sudo_output += buff.value
                time.sleep(0.01)
            password = password + '\n'
            ssh_channel_write(self.channel, c_char_p(password), len(bytes(password)))
            print "password written"
        #ssh_channel_send_eof(self.channel)
        self.sudo=True

    def close(self):
        ssh_channel_close(self.channel)
        ssh_channel_send_eof(self.channel)
        ssh_channel_free(self.channel)



class SftpSession(SshObject):
    def __init__(self, session):
        sftp = sftp_new(session.session)
        rc = sftp_init(sftp)
        self.sftp = sftp
        self.session = session

    def open(self, path, access_type, mode):
        path = c_char_p(path)
        file = SftpFile(self, path, access_type, mode)
        return file

    def close(self):
        sftp_free(self.sftp)

class SftpFile(SshObject):
    def __init__(self, session, path, access_type, mode):
        self.session = session
        self.file = sftp_open(session.sftp, path, access_type, mode)

    def write(self, data):
        rc = sftp_write(self.file, bytes(data), len(bytes(data)))
        err = ssh_get_error(self.session.session.session)
        return rc

    def read(self, dest):
        f = file(dest, 'wb')
        bufflen = 2048
        buff = create_string_buffer(bufflen)
        n = sftp_read(self.file, buff, bufflen)
        while n > 0:
           f.write(buff.value)
           n = sftp_read(self.file, buff, bufflen)
        f.close()

    def close(self):
        rc = sftp_close(self.file)


class ScpSession(SshObject):
    def __init__(self, session):
        self.        rc = ssh_scp_init(self.scp)
        self.session = session

    def __dealloc__(self):
        scp_close(self.scp)
        scp_free(self.scp)
    
