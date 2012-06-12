from ctypes import *
from functools import wraps

try:
    clibssh = cdll.LoadLibrary("libssh.so")
except OSError:
    try:
        clibssh = cdll.LoadLibrary("libssh.dylib")
    except OSError:
        raise Exception("Could not load libssh C library.")

(SSH_OPTIONS_HOST,
    SSH_OPTIONS_PORT,
    SSH_OPTIONS_PORT_STR,
    SSH_OPTIONS_FD,
    SSH_OPTIONS_USER,
    SSH_OPTIONS_SSH_DIR,
    SSH_OPTIONS_IDENTITY,
    SSH_OPTIONS_ADD_IDENTITY,
    SSH_OPTIONS_KNOWNHOSTS,
    SSH_OPTIONS_TIMEOUT,
    SSH_OPTIONS_TIMEOUT_USEC,
    SSH_OPTIONS_SSH1,
    SSH_OPTIONS_SSH2,
    SSH_OPTIONS_LOG_VERBOSITY,
    SSH_OPTIONS_LOG_VERBOSITY_STR,
    SSH_OPTIONS_CIPHERS_C_S,
    SSH_OPTIONS_CIPHERS_S_C,
    SSH_OPTIONS_COMPRESSION_C_S,
    SSH_OPTIONS_COMPRESSION_S_C,
    SSH_OPTIONS_PROXYCOMMAND,
    SSH_OPTIONS_BINDADDR,
    SSH_OPTIONS_STRICTHOSTKEYCHECK,
    SSH_OPTIONS_COMPRESSION,
    SSH_OPTIONS_COMPRESSION_LEVEL
) = range(24)

(SSH_FX_OK,
    SSH_FX_EOF,
    SSH_FX_NO_SUCH_FILE,
    SSH_FX_PERMISSION_DENIED,
    SSH_FX_FAILURE,
    SSH_FX_BAD_MESSAGE,
    SSH_FX_NO_CONNECTION,
    SSH_FX_CONNECTION_LOST,
    SSH_FX_OP_UNSUPPORTED,
    SSH_FX_INVALID_HANDLE,
    SSH_FX_NO_SUCH_PATH,
    SSH_FX_FILE_ALREADY_EXISTS,
    SSH_FX_WRITE_PROTECT,
    SSH_FX_NO_MEDIA,
) = range(14)


SSH_SCP_WRITE = 0
SSH_SCP_READ = 1
SSH_SCP_RECURSIVE = 0x10

NULL = 0
SSH_EOF = -127
SSH_OK = 0


def libssh(restype=None, argtypes=None):
    def wrapper(f):
        fname = f.__name__
        cfunc = getattr(clibssh, f.__name__)
        if restype is not None:
            cfunc.restype = restype
        if argtypes is not None:
            cfunc.argtypes = argtypes

        @wraps(f) 
        def new_func(*args):
            return cfunc(*args)
        return new_func
    return wrapper


@libssh(restype=c_char_p, argtypes=[c_void_p])
def ssh_get_error(session): pass

@libssh(restype=c_void_p)
def ssh_new(): pass

@libssh(argtypes=[c_void_p])
def ssh_free(session): pass

@libssh(argtypes=[c_void_p, c_int, c_char_p])
def ssh_options_set(session, opt_code, opt): pass

@libssh(argtypes=[c_void_p])
def ssh_connect(session): pass

@libssh(argtypes=[c_void_p])
def ssh_is_server_known(session): pass

@libssh(argtypes=[c_void_p])
def ssh_disconnect(session): pass

@libssh(argtypes=[c_void_p, c_char_p, c_char_p])
def ssh_userauth_password(session, username, password): pass

@libssh(argtypes=[c_void_p, c_char_p])
def ssh_userauth_autopubkey(session, username): pass

@libssh(argtypes=[c_void_p])
def ssh_get_fd(session): pass

@libssh(argtypes=[c_void_p], restype=c_void_p)
def ssh_channel_new(session): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_free(channel): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_open_session(channel): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_close(channel): pass

@libssh(argtypes=[c_void_p, c_char_p])
def ssh_channel_request_exec(channel, command): pass

@libssh(argtypes=[c_void_p, c_int])
def ssh_channel_poll(channel, is_stderr): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int, c_int])
def ssh_channel_read(channel, buffer, bufferlen, is_stderr): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_send_eof(channel): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_request_pty(channel): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int])
def ssh_channel_write(channel, data, datalen): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_request_shell(channel): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_is_open(channel): pass

@libssh(argtypes=[c_void_p])
def ssh_channel_is_eof(channel): pass

@libssh(argtypes=[c_void_p], restype=c_void_p)
def ssh_scp_new(session): pass

@libssh(argtypes=[c_void_p])
def ssh_scp_init(scp_session): pass

@libssh(argtypes=[c_void_p])
def ssh_scp_leave_directory(scp_session): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int])
def ssh_scp_push_directory(scp_ession, path, mode): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int, c_int]) 
def ssh_scp_push_file(scp_session, filename, datalen, mode): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int])
def ssh_scp_write(scp_session, data, datalen): pass

@libssh(argtypes=[c_void_p])
def ssh_scp_close(scp_session): pass

@libssh(argtypes=[c_void_p])
def ssh_scp_free(scp_session): pass

@libssh(argtypes=[c_void_p], restype=c_void_p)
def sftp_new(session): pass

@libssh(argtypes=[c_void_p])
def sftp_init(sftp_session): pass

@libssh(argtypes=[c_void_p])
def sftp_close(sftp_session): pass

@libssh(argtypes=[c_void_p])
def sftp_free(sftp_session): pass

@libssh(argtypes=[c_void_p])
def sftp_get_error(sftp_session): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int])
def sftp_mkdir(sftp_session, path, mode): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int, c_int])
def sftp_open(sftp_session, filename, access_type, mode): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int])
def sftp_write(file_handle, data, datalen): pass

@libssh(argtypes=[c_void_p, c_char_p, c_int])
def sftp_read(file_handle, buffer, bufferlen): pass

