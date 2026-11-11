// ALIS launcher — native entry point of ALIS.app.
//
// macOS (TCC) attributes file access to the "responsible process". A bare
// launchd job or a shell-script bundle executable is seen as /bin/bash and is
// silently denied access to Google Drive (File Provider). This native stub
// stays alive as the responsible process (bundle id ovh.aiad.alis) and runs
// Contents/Resources/alis-launcher.sh as a child, forwarding its arguments
// and exit status.
//
// Build: launcher/build.sh
#include <libgen.h>
#include <mach-o/dyld.h>
#include <limits.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

extern char **environ;

int main(int argc, char *argv[]) {
    char exe[PATH_MAX];
    uint32_t size = sizeof(exe);
    if (_NSGetExecutablePath(exe, &size) != 0) return 70;
    char resolved[PATH_MAX];
    if (realpath(exe, resolved) == NULL) return 70;

    char script[PATH_MAX];
    // <App>/Contents/MacOS/alis-launcher -> <App>/Contents/Resources/alis-launcher.sh
    snprintf(script, sizeof(script), "%s/../Resources/alis-launcher.sh", dirname(resolved));

    char **child_argv = calloc((size_t)argc + 2, sizeof(char *));
    if (child_argv == NULL) return 70;
    child_argv[0] = "/bin/bash";
    child_argv[1] = script;
    for (int i = 1; i < argc; i++) child_argv[i + 1] = argv[i];

    pid_t pid;
    if (posix_spawn(&pid, "/bin/bash", NULL, NULL, child_argv, environ) != 0) return 71;
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) return 71;
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
