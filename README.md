<p align="center">
  <img src="gitDumper-icon.png" alt="gitDumper Icon" width="300" height="300" style="object-fit: cover;">
</p>


# 🧲 gitDumper

`gitDumper` adalah tool Python untuk mengunduh dan memulihkan folder `.git` yang terekspos secara publik. Sangat cocok dikombinasikan dengan hasil output dari [`gitFinder`](https://github.com/Arifmaulanaazis/gitFinder) untuk dump `.git` secara batch.

> ⚠️ **DISCLAIMER:** Proyek ini dibuat **hanya untuk tujuan edukasi dan penelitian**. Penulis tidak bertanggung jawab atas penyalahgunaan tool ini.

---

## 📦 Instalasi

### 🔹 1. Clone Repositori

```bash
git clone https://github.com/Arifmaulanaazis/gitDumper.git
cd gitDumper
```

### 🔹 2. Jalankan

Tidak perlu install requirements manual — library akan diinstal otomatis saat runtime.

Namun jika ingin menginstal dependensi secara manual:

```bash
pip install -r requirements.txt
```

### 🔹 3. (Opsional) Tambahkan ke PATH

Agar bisa dijalankan dari mana saja:

```bash
chmod +x gitDumper.py
ln -s "$(pwd)/gitDumper.py" /usr/local/bin/gitdumper
```

Sekarang kamu bisa menjalankan:

```bash
gitdumper http://target.com/.git/
```

---

## 🚀 Cara Pakai

### 🟢 Dump dari satu URL

```bash
python gitDumper.py http://example.com/.git/
```

### 🟢 Dump dari file CSV hasil `gitFinder`

```bash
python gitDumper.py hasil_scan.csv --kolom "Git URL" --statuscode 200
```

---

## 🔄 Integrasi dengan [gitFinder](https://github.com/Arifmaulanaazis/gitFinder)

1. Jalankan `gitFinder` untuk mencari endpoint `.git` terbuka.
2. Simpan hasil ke file CSV.
3. Gunakan `gitDumper` untuk batch download berdasarkan hasil scan:

```bash
python gitDumper.py hasil_gitfinder.csv --kolom "Git URL" --statuscode 200
```

---

## 📂 Output

Semua dump `.git` akan disimpan dalam folder berdasarkan domain:

```
output/
└── example.com/
    └── .git/
```

Untuk memulihkan:

```bash
cd example.com && git checkout -- .
```

---

## ✨ Fitur

- 📥 Download otomatis semua file dan object dari folder `.git`
- 🔍 Ekstrak SHA1 dari `index`, `logs`, `refs`, dll.
- 💡 Deteksi dan download file `.pack` & `.idx`
- 🧪 Parsing `index` menggunakan mmap + struct
- 🎨 TQDM + Rich logging
- 🔄 Support auto-batch dari CSV


## 👨‍💻 Kontribusi

Pull Request sangat diterima! Jika kamu ingin menambahkan fitur atau memperbaiki bug:

1. Fork repo ini
2. Buat branch fitur: `git checkout -b fitur-baru`
3. Commit perubahan: `git commit -m 'Tambah fitur A'`
4. Push ke branch: `git push origin fitur-baru`
5. Buat Pull Request

---

## ⚖️ Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).

---

## ⚠️ Disclaimer

Tool ini dibuat **hanya untuk tujuan edukasi dan penelitian**. Penggunaan terhadap domain atau sistem tanpa izin eksplisit dari pemiliknya **dilarang keras** dan dapat melanggar hukum yang berlaku. Pengembang tidak bertanggung jawab atas penyalahgunaan tool ini.

---

## 📫 Kontak

Dikembangkan oleh [@Arifmaulanaazis](https://github.com/Arifmaulanaazis). Jangan ragu untuk membuka issue jika ada pertanyaan atau bug yang ditemukan.
