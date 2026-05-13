/* Copyright (c) 2026 Qorix */

#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int main(int argc, char** argv) {
    struct sockaddr_un addr;
    int fd;
    const char* path;
    size_t path_len;
    int rc;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <socket-path>\n", argv[0]);
        return 2;
    }

    path = argv[1];
    path_len = strlen(path);
    if (path_len >= sizeof(addr.sun_path)) {
        fprintf(stderr, "path too long: %s\n", path);
        return 2;
    }

    fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        printf("socket failed: errno=%d %s\n", errno, strerror(errno));
        return 1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    memcpy(addr.sun_path, path, path_len + 1U);

    unlink(path);
    rc = bind(fd, (const struct sockaddr*)&addr, sizeof(addr));
    if (rc != 0) {
        printf("bind failed: path=%s errno=%d %s\n", path, errno, strerror(errno));
        close(fd);
        return 1;
    }

    printf("bind ok: path=%s\n", path);
    close(fd);
    unlink(path);
    return 0;
}