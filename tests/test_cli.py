import socket

from vgdb import cli


def test_a_free_port_means_no_instance():
    with socket.socket() as free:
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]

    assert cli.instance_running(port) is False


def test_a_busy_port_means_an_instance_is_already_up():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()

        assert cli.instance_running(busy.getsockname()[1]) is True
