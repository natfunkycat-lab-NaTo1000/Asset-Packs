/**
 * Asset-Packs Full-Stack Downloader
 *
 * Downloads asset packs for Momentum Firmware from the official API.
 * API: https://up.momentum-fw.dev/asset-packs
 *
 * Usage:
 *   asset-pack-dl --list
 *   asset-pack-dl --download <pack-name> [--format zip|tar.gz] [--output <dir>]
 *   asset-pack-dl --all [--format zip|tar.gz] [--output <dir>]
 *
 * Requirements:
 *   libcurl (libcurl4-openssl-dev or equivalent)
 */

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <curl/curl.h>

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
// Minimal JSON helpers (no external dependency)
// ---------------------------------------------------------------------------

/**
 * Extract a string value from a flat JSON object for a given key.
 * Only handles simple string values (no nesting needed for pack metadata).
 */
static std::string json_get_string(const std::string &json, const std::string &key) {
    // Look for "key":"value" or "key": "value"
    std::string search = "\"" + key + "\"";
    std::size_t pos = json.find(search);
    if (pos == std::string::npos) return "";

    pos = json.find(':', pos + search.size());
    if (pos == std::string::npos) return "";
    ++pos;

    // Skip whitespace
    while (pos < json.size() && (json[pos] == ' ' || json[pos] == '\t' || json[pos] == '\n' || json[pos] == '\r'))
        ++pos;

    if (pos >= json.size() || json[pos] != '"') return "";
    ++pos;

    std::string value;
    while (pos < json.size() && json[pos] != '"') {
        if (json[pos] == '\\' && pos + 1 < json.size()) {
            ++pos;
            switch (json[pos]) {
                case '"':  value += '"';  break;
                case '\\': value += '\\'; break;
                case '/':  value += '/';  break;
                case 'n':  value += '\n'; break;
                case 'r':  value += '\r'; break;
                case 't':  value += '\t'; break;
                default:   value += json[pos]; break;
            }
        } else {
            value += json[pos];
        }
        ++pos;
    }
    return value;
}

/**
 * Split a JSON array string into individual object strings.
 * Handles one level of nesting (objects inside an array).
 */
static std::vector<std::string> json_split_array(const std::string &json) {
    std::vector<std::string> items;

    // Find the opening bracket of the array
    std::size_t start = json.find('[');
    if (start == std::string::npos) return items;
    ++start;

    int depth = 0;
    std::size_t obj_start = std::string::npos;

    for (std::size_t i = start; i < json.size(); ++i) {
        char c = json[i];
        if (c == '{') {
            if (depth == 0) obj_start = i;
            ++depth;
        } else if (c == '}') {
            --depth;
            if (depth == 0 && obj_start != std::string::npos) {
                items.push_back(json.substr(obj_start, i - obj_start + 1));
                obj_start = std::string::npos;
            }
        }
    }
    return items;
}

// ---------------------------------------------------------------------------
// Pack metadata
// ---------------------------------------------------------------------------

struct AssetPack {
    std::string id;
    std::string name;
    std::string author;
    std::string description;
    std::string url_zip;
    std::string url_tar;
};

// ---------------------------------------------------------------------------
// libcurl callbacks
// ---------------------------------------------------------------------------

static std::size_t write_string_cb(char *ptr, std::size_t size, std::size_t nmemb, void *userdata) {
    auto *str = static_cast<std::string *>(userdata);
    str->append(ptr, size * nmemb);
    return size * nmemb;
}

struct DownloadCtx {
    std::FILE *file      = nullptr;
    curl_off_t total     = 0;
    curl_off_t received  = 0;
    std::string pack_name;
};

static int progress_cb(void *userdata, curl_off_t dltotal, curl_off_t dlnow,
                       curl_off_t /*ultotal*/, curl_off_t /*ulnow*/) {
    auto *ctx = static_cast<DownloadCtx *>(userdata);
    ctx->total    = dltotal;
    ctx->received = dlnow;

    if (dltotal > 0) {
        int percent = static_cast<int>(100.0 * dlnow / dltotal);
        // Simple progress bar (50 chars wide)
        int filled = percent / 2;
        std::printf("\r  [%-50s] %3d%% %6.1f KB / %6.1f KB",
                    std::string(filled, '#').append(50 - filled, '-').c_str(),
                    percent,
                    dlnow / 1024.0,
                    dltotal / 1024.0);
        std::fflush(stdout);
    }
    return 0; // returning non-zero aborts the transfer
}

static std::size_t write_file_cb(char *ptr, std::size_t size, std::size_t nmemb, void *userdata) {
    auto *ctx = static_cast<DownloadCtx *>(userdata);
    return std::fwrite(ptr, size, nmemb, ctx->file);
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

class CurlGlobal {
public:
    CurlGlobal()  { curl_global_init(CURL_GLOBAL_DEFAULT); }
    ~CurlGlobal() { curl_global_cleanup(); }
    CurlGlobal(const CurlGlobal &)            = delete;
    CurlGlobal &operator=(const CurlGlobal &) = delete;
};

/**
 * Perform a simple GET request and return the response body as a string.
 */
static std::string http_get(const std::string &url) {
    CURL *curl = curl_easy_init();
    if (!curl) throw std::runtime_error("curl_easy_init() failed");

    std::string body;
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_string_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &body);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "asset-pack-dl/1.0");
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);

    CURLcode res = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        throw std::runtime_error(std::string("HTTP GET failed: ") + curl_easy_strerror(res));
    }
    if (http_code < 200 || http_code >= 300) {
        throw std::runtime_error("HTTP error " + std::to_string(http_code) + " for URL: " + url);
    }
    return body;
}

/**
 * Download a URL to a local file, showing progress.
 */
static void http_download(const std::string &url, const fs::path &dest,
                           const std::string &pack_name) {
    CURL *curl = curl_easy_init();
    if (!curl) throw std::runtime_error("curl_easy_init() failed");

    std::FILE *fp = std::fopen(dest.string().c_str(), "wb");
    if (!fp) {
        curl_easy_cleanup(curl);
        throw std::runtime_error("Cannot open file for writing: " + dest.string());
    }

    DownloadCtx ctx;
    ctx.file      = fp;
    ctx.pack_name = pack_name;

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_file_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &ctx);
    curl_easy_setopt(curl, CURLOPT_XFERINFOFUNCTION, progress_cb);
    curl_easy_setopt(curl, CURLOPT_XFERINFODATA, &ctx);
    curl_easy_setopt(curl, CURLOPT_NOPROGRESS, 0L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "asset-pack-dl/1.0");
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 300L); // 5-minute timeout per file

    CURLcode res = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    curl_easy_cleanup(curl);
    std::fclose(fp);

    std::printf("\n"); // newline after progress bar

    if (res != CURLE_OK) {
        fs::remove(dest);
        throw std::runtime_error(std::string("Download failed: ") + curl_easy_strerror(res));
    }
    if (http_code < 200 || http_code >= 300) {
        fs::remove(dest);
        throw std::runtime_error("HTTP error " + std::to_string(http_code) + " downloading: " + url);
    }
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

static const std::string API_BASE = "https://up.momentum-fw.dev/asset-packs";

/**
 * Fetch and parse the pack index from the API.
 */
static std::vector<AssetPack> fetch_packs() {
    std::string body = http_get(API_BASE);

    std::vector<AssetPack> packs;
    for (const auto &obj : json_split_array(body)) {
        AssetPack p;
        p.id          = json_get_string(obj, "id");
        p.name        = json_get_string(obj, "name");
        p.author      = json_get_string(obj, "author");
        p.description = json_get_string(obj, "description");
        p.url_zip     = json_get_string(obj, "url_zip");
        p.url_tar     = json_get_string(obj, "url_tar");
        if (!p.id.empty()) packs.push_back(std::move(p));
    }
    return packs;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

static void cmd_list(const std::vector<AssetPack> &packs) {
    if (packs.empty()) {
        std::cout << "No asset packs found.\n";
        return;
    }
    std::cout << "Available asset packs (" << packs.size() << "):\n\n";
    for (const auto &p : packs) {
        std::cout << "  ID:          " << p.id          << "\n";
        std::cout << "  Name:        " << p.name        << "\n";
        std::cout << "  Author:      " << p.author      << "\n";
        std::cout << "  Description: " << p.description << "\n";
        std::cout << "\n";
    }
}

static void cmd_download(const AssetPack &pack, const std::string &format, const fs::path &output_dir) {
    fs::create_directories(output_dir);

    std::string url;
    std::string ext;

    if (format == "tar.gz") {
        url = pack.url_tar;
        ext = ".tar.gz";
    } else {
        url = pack.url_zip;
        ext = ".zip";
    }

    if (url.empty()) {
        throw std::runtime_error("No " + format + " URL available for pack: " + pack.id);
    }

    fs::path dest = output_dir / (pack.id + ext);
    std::cout << "Downloading '" << pack.name << "' (" << pack.id << ") as " << format << "...\n";
    http_download(url, dest, pack.id);
    std::cout << "  Saved to: " << dest.string() << "\n";
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

static void print_usage(const char *argv0) {
    std::cout
        << "Asset-Packs Full-Stack Downloader v1.0\n"
        << "Downloads asset packs for Momentum Firmware (Flipper Zero)\n\n"
        << "Usage:\n"
        << "  " << argv0 << " --list\n"
        << "      List all available asset packs\n\n"
        << "  " << argv0 << " --download <pack-id> [options]\n"
        << "      Download a specific asset pack\n\n"
        << "  " << argv0 << " --all [options]\n"
        << "      Download all asset packs\n\n"
        << "Options:\n"
        << "  --format <fmt>   Download format: zip (default) or tar.gz\n"
        << "  --output <dir>   Output directory (default: current directory)\n"
        << "  --help           Show this help message\n\n"
        << "Examples:\n"
        << "  " << argv0 << " --list\n"
        << "  " << argv0 << " --download black-flags\n"
        << "  " << argv0 << " --download pokemon --format tar.gz --output ~/packs\n"
        << "  " << argv0 << " --all --output ~/all-packs\n";
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    // Parse arguments
    bool do_list     = false;
    bool do_all      = false;
    std::string download_id;
    std::string format     = "zip";
    std::string output_dir = ".";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "--list") {
            do_list = true;
        } else if (arg == "--all") {
            do_all = true;
        } else if (arg == "--download") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --download requires a pack ID argument\n";
                return 1;
            }
            download_id = argv[++i];
        } else if (arg == "--format") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --format requires an argument (zip or tar.gz)\n";
                return 1;
            }
            format = argv[++i];
            if (format != "zip" && format != "tar.gz") {
                std::cerr << "Error: --format must be 'zip' or 'tar.gz'\n";
                return 1;
            }
        } else if (arg == "--output") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --output requires a directory argument\n";
                return 1;
            }
            output_dir = argv[++i];
        } else {
            std::cerr << "Error: Unknown argument: " << arg << "\n";
            print_usage(argv[0]);
            return 1;
        }
    }

    if (!do_list && !do_all && download_id.empty()) {
        std::cerr << "Error: No action specified. Use --list, --download, or --all.\n";
        print_usage(argv[0]);
        return 1;
    }

    CurlGlobal curl_global;

    try {
        if (do_list) {
            std::cout << "Fetching pack list from " << API_BASE << " ...\n\n";
            auto packs = fetch_packs();
            cmd_list(packs);
            return 0;
        }

        if (!download_id.empty()) {
            std::cout << "Fetching pack list from " << API_BASE << " ...\n";
            auto packs = fetch_packs();
            auto it = std::find_if(packs.begin(), packs.end(),
                                   [&](const AssetPack &p) { return p.id == download_id; });
            if (it == packs.end()) {
                std::cerr << "Error: Pack '" << download_id << "' not found.\n";
                std::cerr << "Run with --list to see available packs.\n";
                return 1;
            }
            cmd_download(*it, format, output_dir);
            return 0;
        }

        if (do_all) {
            std::cout << "Fetching pack list from " << API_BASE << " ...\n\n";
            auto packs = fetch_packs();
            if (packs.empty()) {
                std::cout << "No packs found.\n";
                return 0;
            }
            std::cout << "Downloading " << packs.size() << " packs to '" << output_dir << "'...\n\n";
            int ok = 0, fail = 0;
            for (const auto &pack : packs) {
                try {
                    cmd_download(pack, format, output_dir);
                    ++ok;
                } catch (const std::exception &e) {
                    std::cerr << "  Warning: Failed to download '" << pack.id << "': " << e.what() << "\n";
                    ++fail;
                }
            }
            std::cout << "\nDone. " << ok << " downloaded, " << fail << " failed.\n";
            return fail > 0 ? 1 : 0;
        }
    } catch (const std::exception &e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
