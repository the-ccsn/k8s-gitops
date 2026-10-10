#define _GNU_SOURCE
#include <link.h>
#include <stdint.h>
#include <string.h>

/* C++ interface layouts are only valid for this exact stock Envoy build. */
#if defined(__aarch64__)
static const unsigned char supported_id[] = {
    0xb3, 0x30, 0xc4, 0x9f, 0x04, 0xc9, 0x3d, 0xb8, 0xe5, 0x82, 0x33, 0xda, 0x1d, 0x08, 0x60, 0x34
};
#elif defined(__x86_64__)
static const unsigned char supported_id[] = {
    0x7c, 0x8d, 0x12, 0xcf, 0xeb, 0x6e, 0x36, 0x1b, 0xc5, 0x51, 0x16, 0x93, 0xf9, 0x98, 0x24, 0x0e
};
#else
#error Unsupported Envoy module architecture
#endif

static int find_host_id(struct dl_phdr_info *info, size_t size, void *result) {
    (void)size;
    if (info->dlpi_name && info->dlpi_name[0]) return 0;
    for (size_t i = 0; i < info->dlpi_phnum; i++) {
        const ElfW(Phdr) *header = &info->dlpi_phdr[i];
        if (header->p_type != PT_NOTE) continue;
        const unsigned char *note = (const unsigned char *)(info->dlpi_addr + header->p_vaddr);
        size_t remaining = header->p_memsz;
        while (remaining >= sizeof(ElfW(Nhdr))) {
            ElfW(Nhdr) entry;
            memcpy(&entry, note, sizeof(entry));
            size_t name_size = ((size_t)entry.n_namesz + 3) & ~(size_t)3;
            size_t data_size = ((size_t)entry.n_descsz + 3) & ~(size_t)3;
            size_t total = sizeof(entry) + name_size + data_size;
            if (total > remaining) break;
            const unsigned char *name = note + sizeof(entry);
            const unsigned char *data = name + name_size;
            if (entry.n_type == NT_GNU_BUILD_ID && entry.n_namesz == 4 &&
                !memcmp(name, "GNU", 4) && entry.n_descsz == sizeof(supported_id) &&
                !memcmp(data, supported_id, sizeof(supported_id))) {
                *(int *)result = 1;
                return 1;
            }
            note += total;
            remaining -= total;
        }
    }
    return 1;
}

int ccsn_compatible_host(void) {
    int compatible = 0;
    dl_iterate_phdr(find_host_id, &compatible);
    return compatible;
}
