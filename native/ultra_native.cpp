// Optional streaming helper. Python owns inventory, resume validation and verification.
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#include <io.h>
#else
#include <openssl/evp.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;
struct FileCloser { void operator()(FILE* f) const { if (f) fclose(f); } };
using File = std::unique_ptr<FILE, FileCloser>;

File open_file(const fs::path& path, bool output) {
#ifdef _WIN32
    FILE* f = _wfopen(path.c_str(), output ? L"r+b" : L"rb");
#else
    FILE* f = fopen(path.c_str(), output ? "r+b" : "rb");
#endif
    if (!f) throw std::runtime_error("Cannot open file; errno=" + std::to_string(errno));
    return File(f);
}

class Sha256 {
#ifdef _WIN32
    BCRYPT_ALG_HANDLE alg{};
    BCRYPT_HASH_HANDLE hash{};
    std::vector<unsigned char> object;
    void check(NTSTATUS s) { if (s < 0) throw std::runtime_error("BCrypt failed"); }
#else
    EVP_MD_CTX* ctx{};
#endif
public:
    Sha256() {
#ifdef _WIN32
        check(BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0));
        DWORD length{}, got{};
        check(BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&length), sizeof(length), &got, 0));
        object.resize(length);
        check(BCryptCreateHash(alg, &hash, object.data(), length, nullptr, 0, 0));
#else
        ctx = EVP_MD_CTX_new();
        if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr) != 1) throw std::runtime_error("OpenSSL init failed");
#endif
    }
    ~Sha256() {
#ifdef _WIN32
        if (hash) BCryptDestroyHash(hash);
        if (alg) BCryptCloseAlgorithmProvider(alg, 0);
#else
        EVP_MD_CTX_free(ctx);
#endif
    }
    void update(unsigned char* p, size_t n) {
#ifdef _WIN32
        check(BCryptHashData(hash, p, static_cast<ULONG>(n), 0));
#else
        if (EVP_DigestUpdate(ctx, p, n) != 1) throw std::runtime_error("OpenSSL update failed");
#endif
    }
    std::string finish() {
        std::array<unsigned char, 32> out{};
#ifdef _WIN32
        check(BCryptFinishHash(hash, out.data(), static_cast<ULONG>(out.size()), 0));
#else
        unsigned int n{};
        if (EVP_DigestFinal_ex(ctx, out.data(), &n) != 1 || n != out.size()) throw std::runtime_error("OpenSSL final failed");
#endif
        std::ostringstream s;
        for (auto c : out) s << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(c);
        return s.str();
    }
};

int run(const std::vector<fs::path>& args) {
    try {
        if (args.size() != 6 || args[1] != "copy") throw std::runtime_error("Usage: ultra_native copy SOURCE PART OFFSET BUFFER_BYTES");
        auto offset = std::stoull(args[4].string());
        auto buffer_size = std::stoull(args[5].string());
        if (buffer_size < 65536 || buffer_size > 64*1024*1024) throw std::runtime_error("Invalid buffer size");
        if (fs::file_size(args[3]) != offset || fs::file_size(args[2]) < offset) throw std::runtime_error("Invalid resume length");
        auto in = open_file(args[2], false);
        auto out = open_file(args[3], true);
#ifdef _WIN32
        if (_fseeki64(out.get(), static_cast<__int64>(offset), SEEK_SET)) throw std::runtime_error("Seek failed");
#else
        if (fseeko(out.get(), static_cast<off_t>(offset), SEEK_SET)) throw std::runtime_error("Seek failed");
#endif
        std::vector<unsigned char> buffer(buffer_size);
        Sha256 hash;
        unsigned long long position = 0;
        while (size_t n = fread(buffer.data(), 1, buffer.size(), in.get())) {
            hash.update(buffer.data(), n);
            auto skip = position < offset ? std::min<unsigned long long>(offset-position, n) : 0;
            if (n > skip && fwrite(buffer.data()+skip, 1, n-skip, out.get()) != n-skip) throw std::runtime_error("Incomplete write");
            position += n;
        }
        if (ferror(in.get()) || fflush(out.get())) throw std::runtime_error("Read/flush failed");
#ifdef _WIN32
        if (_commit(_fileno(out.get()))) throw std::runtime_error("Sync failed");
#else
        if (fsync(fileno(out.get()))) throw std::runtime_error("Sync failed");
#endif
        std::cout << hash.finish() << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return 1;
    }
}
#ifdef _WIN32
int wmain(int argc, wchar_t** argv) {
    std::vector<fs::path> args;
    for (int i=0; i<argc; ++i) args.emplace_back(argv[i]);
    return run(args);
}
#else
int main(int argc, char** argv) {
    std::vector<fs::path> args;
    for (int i=0; i<argc; ++i) args.emplace_back(argv[i]);
    return run(args);
}
#endif
