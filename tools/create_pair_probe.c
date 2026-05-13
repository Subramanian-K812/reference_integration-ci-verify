/*
 * Copyright (c) Qorix 2026
 */

/**
 * @file create_pair_probe.c
 * @brief Reproduces the QNX create_pair fallback used by iceoryx2.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int set_non_blocking(int fd, const char *label) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) {
        fprintf(stderr, "%s F_GETFL failed: errno=%d %s\n", label, errno, strerror(errno));
        return -1;
    }

    if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
        fprintf(stderr, "%s F_SETFL O_NONBLOCK failed: errno=%d %s\n", label, errno, strerror(errno));
        return -1;
    }

    printf("%s non-blocking set ok\n", label);
    return 0;
}

int main(void) {
    int fds[2] = {-1, -1};

    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fds) == 0) {
        printf("socketpair ok: fd0=%d fd1=%d\n", fds[0], fds[1]);
        if (set_non_blocking(fds[0], "socketpair fd0") != 0) {
            return 2;
        }
        if (set_non_blocking(fds[1], "socketpair fd1") != 0) {
            return 3;
        }
        return 0;
    }

    printf("socketpair failed: errno=%d %s\n", errno, strerror(errno));

    if (pipe(fds) != 0) {
        fprintf(stderr, "pipe failed: errno=%d %s\n", errno, strerror(errno));
        return 4;
    }

    printf("pipe ok: read_fd=%d write_fd=%d\n", fds[0], fds[1]);
    if (set_non_blocking(fds[0], "pipe read_fd") != 0) {
        return 5;
    }
    if (set_non_blocking(fds[1], "pipe write_fd") != 0) {
        return 6;
    }

    return 0;
}