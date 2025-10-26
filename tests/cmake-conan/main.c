#include <stdio.h>
#include <SDL3/SDL_version.h>

/* Code from https://wiki.libsdl.org/SDL3/SDL_GetVersion */
int main(int argc, char **argv) {
    const int compiled = SDL_VERSION;  /* hardcoded number from SDL headers */
    const int linked = SDL_GetVersion();  /* reported by linked SDL library */

    printf("Compile-time SDL version %d.%d.%d\n",
            SDL_VERSIONNUM_MAJOR(compiled),
            SDL_VERSIONNUM_MINOR(compiled),
            SDL_VERSIONNUM_MICRO(compiled));

    printf("Run-time SDL version %d.%d.%d.\n",
            SDL_VERSIONNUM_MAJOR(linked),
            SDL_VERSIONNUM_MINOR(linked),
            SDL_VERSIONNUM_MICRO(linked));
    return 0;
}
