#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(void) {
    int fds[2] = {-1, -1};
    int ret = socketpair(AF_UNIX, SOCK_STREAM, 0, fds);
    if (ret == 0) {
        printf("socketpair ok: %d %d\n", fds[0], fds[1]);
        close(fds[0]);
        close(fds[1]);
        return 0;
    }

    printf("socketpair failed: errno=%d %s\n", errno, strerror(errno));
    return 1;
}
