/*
 * QA shims for extracted Xibo Linux Player (snap 1.8-R6 / Boost 1.70).
 *
 * - Hot-patches Parsing::xmlFrom in the main executable so <settings> children
 *   are promoted to the property-tree root (snap loadFromImpl calls loadField on
 *   the document root; without this, CMS settings never apply).
 * - Interposes boost::filesystem::detail::status so empty paths map to
 *   XIBO_LOCAL_LIBRARY (default /data/xibo-library).
 * - Interposes connect(2) so 127.0.0.1:80 redirects to XIBO_CMS_CONNECT_HOST
 *   (default cms-web) as a safety net if address still defaults briefly.
 *
 * Build against Boost 1.70 headers matching the snap (property_tree is header-only).
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dlfcn.h>
#include <elf.h>
#include <link.h>
#include <sys/mman.h>
#include <unistd.h>

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>

#include <boost/filesystem.hpp>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/xml_parser.hpp>
#include <boost/system/error_code.hpp>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace fs = boost::filesystem;
namespace pt = boost::property_tree;
namespace sys = boost::system;

using FilePath = fs::path;
using status_fn = fs::file_status (*)(const fs::path&, sys::error_code*);
using connect_fn = int (*)(int, const struct sockaddr*, socklen_t);

static const char* library_fallback() {
  const char* fb = std::getenv("XIBO_LOCAL_LIBRARY");
  return (fb && fb[0]) ? fb : "/data/xibo-library";
}

static status_fn real_status() {
  static status_fn fn = nullptr;
  if (!fn) {
    fn = reinterpret_cast<status_fn>(dlsym(
        RTLD_NEXT,
        "_ZN5boost10filesystem6detail6statusERKNS0_4pathEPNS_6system10error_codeE"));
  }
  return fn;
}

static connect_fn real_connect_fn() {
  static connect_fn fn = nullptr;
  if (!fn) {
    fn = reinterpret_cast<connect_fn>(dlsym(RTLD_NEXT, "connect"));
  }
  return fn;
}

namespace boost {
namespace filesystem {
namespace detail {
file_status status(const path& p, system::error_code* ec) {
  status_fn fn = real_status();
  if (!fn) {
    if (ec) {
      ec->assign(1, sys::system_category());
    }
    return file_status(file_type::status_error);
  }
  if (p.empty()) {
    const char* fb = library_fallback();
    std::fprintf(stderr, "[qa_shim] status(\"\") -> \"%s\"\n", fb);
    return fn(path(fb), ec);
  }
  return fn(p, ec);
}
}  // namespace detail
}  // namespace filesystem
}  // namespace boost

extern "C" int connect(int fd, const struct sockaddr* addr, socklen_t len) {
  connect_fn fn = real_connect_fn();
  if (addr && addr->sa_family == AF_INET && len >= sizeof(sockaddr_in)) {
    const auto* in = reinterpret_cast<const sockaddr_in*>(addr);
    if (ntohs(in->sin_port) == 80 && in->sin_addr.s_addr == htonl(0x7f000001u)) {
      const char* host = std::getenv("XIBO_CMS_CONNECT_HOST");
      if (!host || !host[0]) {
        host = "cms-web";
      }
      addrinfo hints{};
      addrinfo* res = nullptr;
      hints.ai_family = AF_INET;
      hints.ai_socktype = SOCK_STREAM;
      if (getaddrinfo(host, "80", &hints, &res) == 0 && res) {
        std::fprintf(stderr, "[qa_shim] connect 127.0.0.1:80 -> %s\n", host);
        const int rc = fn(fd, res->ai_addr, static_cast<socklen_t>(res->ai_addrlen));
        freeaddrinfo(res);
        return rc;
      }
    }
  }
  return fn(fd, addr, len);
}

/* ---- Parsing::xmlFrom hot-patch (main executable, non-PLT) ---- */

static void* g_xml_from_addr = nullptr;

static void promote_settings_root(pt::ptree* out, const char* source_label) {
  if (auto settings = out->get_child_optional("settings")) {
    pt::ptree promoted = *settings;
    out->swap(promoted);
    std::fprintf(stderr, "[qa_shim] xmlFrom: promoted <settings> from %s\n", source_label);
  }
}

static bool write_jmp64(void* from, void* to) {
  auto* page =
      reinterpret_cast<void*>(reinterpret_cast<uintptr_t>(from) & ~static_cast<uintptr_t>(0xfff));
  if (mprotect(page, 0x2000, PROT_READ | PROT_WRITE | PROT_EXEC) != 0) {
    std::perror("[qa_shim] mprotect");
    return false;
  }
  auto* p = reinterpret_cast<unsigned char*>(from);
  // movabs rax, imm64; jmp rax
  p[0] = 0x48;
  p[1] = 0xb8;
  const auto dest = reinterpret_cast<uint64_t>(to);
  std::memcpy(p + 2, &dest, sizeof(dest));
  p[10] = 0xff;
  p[11] = 0xe0;
  return true;
}

static pt::ptree* hooked_xml_from_path(pt::ptree* out, const FilePath& path) {
  // Re-read with matching Boost 1.70 headers and promote <settings> to root.
  // (Snap loadFromImpl loadField()s the document root, not settings.*.)
  new (out) pt::ptree();
  try {
    pt::read_xml(path.string(), *out);
    promote_settings_root(out, path.string().c_str());
    if (path.string().find("cmsSettings") != std::string::npos) {
      const auto addr = out->get<std::string>("cmsAddress", "");
      const auto key = out->get<std::string>("key", "");
      const auto lib = out->get<std::string>("localLibrary", "");
      std::fprintf(stderr,
                   "[qa_shim] cms settings after promote: address=%s key_len=%zu library=%s\n",
                   addr.c_str(), key.size(), lib.c_str());
    }
  } catch (const std::exception& ex) {
    std::fprintf(stderr, "[qa_shim] xmlFrom(path) failed for %s: %s\n", path.string().c_str(),
                 ex.what());
  }
  return out;
}

static uintptr_t exe_load_bias() {
  uintptr_t bias = 0;
  dl_iterate_phdr(
      [](dl_phdr_info* info, size_t, void* data) -> int {
        // Main executable usually has an empty dlpi_name.
        if (info->dlpi_name == nullptr || info->dlpi_name[0] == '\0') {
          *reinterpret_cast<uintptr_t*>(data) = static_cast<uintptr_t>(info->dlpi_addr);
          return 1;
        }
        if (std::strstr(info->dlpi_name, "/player") != nullptr ||
            std::strstr(info->dlpi_name, "/xibo-player") != nullptr) {
          *reinterpret_cast<uintptr_t*>(data) = static_cast<uintptr_t>(info->dlpi_addr);
          return 1;
        }
        return 0;
      },
      &bias);
  return bias;
}

static Elf64_Sym* elf_find_sym(uint8_t* base, const char* name) {
  auto* ehdr = reinterpret_cast<Elf64_Ehdr*>(base);
  auto* shdr = reinterpret_cast<Elf64_Shdr*>(base + ehdr->e_shoff);
  Elf64_Shdr* dynsym = nullptr;
  Elf64_Shdr* dynstr = nullptr;
  Elf64_Shdr* symtab = nullptr;
  Elf64_Shdr* strtab = nullptr;
  for (int i = 0; i < ehdr->e_shnum; ++i) {
    if (shdr[i].sh_type == SHT_DYNSYM) {
      dynsym = &shdr[i];
    }
    if (shdr[i].sh_type == SHT_SYMTAB) {
      symtab = &shdr[i];
    }
  }
  if (dynsym) {
    dynstr = &shdr[dynsym->sh_link];
  }
  if (symtab) {
    strtab = &shdr[symtab->sh_link];
  }
  auto scan = [&](Elf64_Shdr* sym_hdr, Elf64_Shdr* str_hdr) -> Elf64_Sym* {
    if (!sym_hdr || !str_hdr) {
      return nullptr;
    }
    auto* syms = reinterpret_cast<Elf64_Sym*>(base + sym_hdr->sh_offset);
    const char* strs = reinterpret_cast<char*>(base + str_hdr->sh_offset);
    const size_t count = sym_hdr->sh_size / sizeof(Elf64_Sym);
    for (size_t i = 0; i < count; ++i) {
      if (syms[i].st_name && std::strcmp(strs + syms[i].st_name, name) == 0) {
        return &syms[i];
      }
    }
    return nullptr;
  };
  if (auto* s = scan(symtab, strtab)) {
    return s;
  }
  return scan(dynsym, dynstr);
}

static void install_xml_from_patch() {
  FILE* f = std::fopen("/proc/self/exe", "rb");
  if (!f) {
    std::perror("[qa_shim] fopen exe");
    return;
  }
  std::fseek(f, 0, SEEK_END);
  const long sz = std::ftell(f);
  std::fseek(f, 0, SEEK_SET);
  if (sz <= 0) {
    std::fclose(f);
    return;
  }
  std::vector<uint8_t> buf(static_cast<size_t>(sz));
  if (std::fread(buf.data(), 1, buf.size(), f) != buf.size()) {
    std::fclose(f);
    std::fprintf(stderr, "[qa_shim] read exe failed\n");
    return;
  }
  std::fclose(f);

  const uintptr_t bias = exe_load_bias();
  const char* path_sym = "_ZN7Parsing7xmlFromB5cxx11ERK8FilePath";
  Elf64_Sym* path = elf_find_sym(buf.data(), path_sym);

  // Known offset for xibo-player snap 1.8-R6 (stable) if .symtab is absent.
  // Only patch the FilePath overload — the string overload parses SOAP responses.
  const uintptr_t path_off = path ? path->st_value : 0x2d7700u;
  g_xml_from_addr = reinterpret_cast<void*>(bias + path_off);
  if (write_jmp64(g_xml_from_addr, reinterpret_cast<void*>(&hooked_xml_from_path))) {
    std::fprintf(stderr, "[qa_shim] patched xmlFrom(FilePath) at %p (bias=%p sym=%s)\n",
                 g_xml_from_addr, reinterpret_cast<void*>(bias), path ? "yes" : "fallback");
  }
}

__attribute__((constructor)) static void qa_shim_init() {
  char exe_path[4096];
  const ssize_t n = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
  if (n <= 0) {
    return;
  }
  exe_path[n] = '\0';
  // Only the player binary — not helpers under /opt/xibo-player/ (gst-plugin-scanner, etc.).
  const char* base = std::strrchr(exe_path, '/');
  base = base ? base + 1 : exe_path;
  if (std::strcmp(base, "player") != 0 && std::strcmp(base, "xibo-player") != 0) {
    return;
  }
  install_xml_from_patch();
}
