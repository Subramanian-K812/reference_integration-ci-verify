#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    int fds[2] = {-1, -1};
    if (pipe(fds) != 0) {
        printf("pipe failed: errno=%d %s\n", errno, strerror(errno));
        return 1;
    }
    printf("pipe ok: read=%d write=%d\n", fds[0], fds[1]);

    for (int i = 0; i < 2; ++i) {
        int flags = fcntl(fds[i], F_GETFL, 0);
        printf("fcntl get fd[%d]=%d flags=%d errno=%d %s\n", i, fds[i], flags, errno, strerror(errno));
        if (flags >= 0) {
            int ret = fcntl(fds[i], F_SETFL, flags | O_NONBLOCK);
            printf("fcntl set fd[%d]=%d ret=%d errno=%d %s\n", i, fds[i], ret, errno, strerror(errno));
        }
    }

    char c = 42;
    int w = write(fds[1], &c, 1);
    printf("write ret=%d errno=%d %s\n", w, errno, strerror(errno));
    c = 0;
    int r = read(fds[0], &c, 1);
    printf("read ret=%d value=%d errno=%d %s\n", r, c, errno, strerror(errno));
    return 0;
}
